"""Observe real output codes and comparator handshakes without driving the DUT."""
import bisect
import cmath
import math
import re
from regression.common.psf import read_psf,interpolate

def edges(t,v,level,direction):
    result=[]
    for i in range(1,len(t)):
        crossed=(v[i-1]<level<=v[i]) if direction==1 else (v[i-1]>=level>v[i])
        if crossed:
            result.append(t[i-1]+(level-v[i-1])*(t[i]-t[i-1])/(v[i]-v[i-1]))
    return result

def fft_codes(codes,fs,k):
    n=len(codes)
    power=[]
    for j in range(n//2+1):
        value=sum(x*cmath.exp(-2j*math.pi*j*i/n) for i,x in enumerate(codes))/n
        power.append(abs(value)**2*(1 if j in (0,n//2) else 2))
    residual=sum(p for j,p in enumerate(power) if j not in (0,k))
    return {'sndr_db':10*math.log10(power[k]/residual),'power':power,
        'frequency_hz':[j*fs/n for j in range(n//2+1)],'sample_rate_hz':fs}

def integral(t,v,start,stop):
    left=bisect.bisect_right(t,start);right=bisect.bisect_left(t,stop)
    tt=[start]+t[left:right]+[stop]
    yy=[interpolate(t,v,start)]+v[left:right]+[interpolate(t,v,stop)]
    return sum((b-a)*(x+y)/2 for a,b,x,y in zip(tt,tt[1:],yy,yy[1:]))

def measure_sar(case,raw):
    cfg=case['measurement'];wave=read_psf(raw/'tran.tran.tran');t=wave['time']
    sample=wave['I_adc.Sample'];starts=edges(t,sample,.9,1);ends=edges(t,sample,.9,-1)
    completes=edges(t,wave['I_adc.Valid'],.9,1)
    evaluates=edges(t,wave['I_adc.ClkC'],.9,-1)
    done=edges(t,wave['EOC'],.9,1)
    discard=cfg['discard_cycles'];n=cfg['n'];period=cfg['expected_period_s']
    selected=ends[discard:discard+n]
    if len(selected)!=n:raise ValueError('Insufficient consecutive sampling events: '+str(len(selected)))
    codes=[];invalid=incomplete=count_errors=mismatches=far_errors=hold_errors=0;details=[];traces=[];errors=[];margins=[]
    physical=cfg.get('physical_frontend',False)
    physical_ref=None
    if physical:
        if 'charge_reference_by_condition' in cfg:
            key=case['condition']['corner']+'_'+str(case['condition']['tokens']['TEMP'])
            physical_ref=cfg['charge_reference_by_condition'][key]
        else:physical_ref={'charge_gain':cfg['charge_gain'],'source':cfg['charge_gain_source']}
    diff_errors=[];switch_errors=code_capture_errors=eval_count_errors=monotonic_errors=0;gate_at_start=[];first_eval_delays=[]
    bottom_edges={}
    if physical:
        for side in ('p','n'):
            for bit in range(9,0,-1):
                name=f'B{side}{bit}';values=wave['I_adc.'+name]
                bottom_edges[name]={direction:edges(t,values,.9,direction) for direction in (-1,1)}
    for index,end in enumerate(selected):
        read=end+cfg['read_offset_s'];code=0
        for bit in range(cfg['bits']):
            v=interpolate(t,wave['D'+str(bit)],read)
            if v>=cfg['logic_high_v']:code|=1<<bit
            elif v>cfg['logic_low_v']:invalid+=1
        stop=starts[bisect.bisect_right(starts,end)]
        valid_times=completes[bisect.bisect_right(completes,end):bisect.bisect_left(completes,stop)]
        eval_count_errors+=int(bisect.bisect_left(evaluates,stop)-bisect.bisect_right(evaluates,end)!=cfg['bits'])
        done_times=done[bisect.bisect_right(done,end):bisect.bisect_left(done,stop)]
        if len(done_times)!=1 or done_times[0]>=read:incomplete+=1
        if len(done_times)==1:margins.append(stop-done_times[0])
        count_errors+=int(len(valid_times)!=cfg['bits'])
        vp=interpolate(t,wave['Vinp'],end);vn=interpolate(t,wave['Vinn'],end)
        expected=min(1023,max(0,math.floor(((vp-vn)+1.8)/3.6*1024)))
        mismatches+=int(code!=expected)
        codes.append(code);details.append(dict(index=index,sample_time_s=end,read_time_s=read,code=code,expected=expected,comparisons=len(valid_times),eoc=done_times))
        if physical:
            next_done_index=bisect.bisect_right(done,read)
            if next_done_index==len(done):hold_errors+=1
            else:
                left=bisect.bisect_right(t,read);right=bisect.bisect_left(t,done[next_done_index])
                for bit in range(cfg['bits']):
                    held=wave['D'+str(bit)][left:right]
                    if held:hold_errors+=int(min(held)<cfg['logic_high_v'] if code&(1<<bit) else max(held)>cfg['logic_low_v'])
        rp,rn=vp,vn
        if physical and valid_times:
            first_eval=evaluates[bisect.bisect_right(evaluates,valid_times[0])-1]
            rp=interpolate(t,wave['I_adc.Vp'],first_eval-20e-12)
            rn=interpolate(t,wave['I_adc.Vn'],first_eval-20e-12)
            first_eval_delays.append(first_eval-end)
            gate_at_start.extend(interpolate(t,wave['I_adc.I_frontend.'+s],first_eval) for s in ('Gp','Gn'))
        decision_code=0;bottoms={f'B{s}{b}':1.8 for s in ('p','n') for b in range(9,0,-1)}
        for j,when in enumerate(valid_times):
            ap=interpolate(t,wave['I_adc.Vp'],when);an=interpolate(t,wave['I_adc.Vn'],when)
            decision=int(interpolate(t,wave['I_adc.Outp'],when+5e-12)>=.9)
            decision_code=(decision_code<<1)|decision
            ideal=int(rp>=rn)
            far_errors+=int(decision!=ideal and abs(rp-rn)>.5*cfg['lsb_v'])
            traces.append(dict(sample=index,bit=9-j,time_s=when,vp=ap,vn=an,diff=ap-an,cm=(ap+an)/2,decision=decision,ideal_diff=rp-rn,ideal_cm=(rp+rn)/2))
            errors.extend([abs(ap-rp),abs(an-rn)])
            if physical:
                evaluate=evaluates[bisect.bisect_right(evaluates,when)-1]
                before_p=interpolate(t,wave['I_adc.Vp'],evaluate-10e-12)
                before_n=interpolate(t,wave['I_adc.Vn'],evaluate-10e-12)
                diff_errors.append((before_p-before_n)-(rp-rn))
                pending={name:interpolate(t,wave['I_adc.'+name],evaluate-10e-12) for name,value in bottoms.items() if abs(interpolate(t,wave['I_adc.'+name],evaluate-10e-12)-value)>.18}
                switch_errors+=int(bool(pending))
                traces[-1].update(evaluate_time_s=evaluate,before_evaluate_vp=before_p,before_evaluate_vn=before_n,pending_bottoms=pending)
            if j<9:
                delta=1.8/(2**(j+1))*(physical_ref['charge_gain'] if physical else 1)
                if (ideal if cfg.get('behavioral_alignment') else decision):rp-=delta
                else:rn-=delta
                bottoms[f'B{"p" if decision else "n"}{9-j}']=0
        if physical and len(valid_times)==10:
            code_capture_errors+=int(code!=decision_code)
            details[-1]['decision_code']=decision_code
            for name,value in bottoms.items():
                counts={d:bisect.bisect_left(v,stop)-bisect.bisect_right(v,end) for d,v in bottom_edges[name].items()}
                monotonic_errors+=int(counts[-1]!=int(value==0) or counts[1]!=0)
    fs=(len(selected)-1)/(selected[-1]-selected[0])
    fin=float(case['condition']['tokens']['FIN']);k=round(fin*n/fs)
    spec=fft_codes(codes,fs,k) if cfg.get('fft',True) else None
    power={}
    begin=selected[0];end=begin+n/fs
    for supply,voltage in [('VDD',1.8),('VREFP',1.8),('VCM',.9)]:
        power[supply+'_w']=-voltage*integral(t,wave[supply+':p'],begin,end)/(end-begin)
    power['clock_input_w']=-integral(t,[a*b for a,b in zip(wave['Clks'],wave['Vclock:p'])],begin,end)/(end-begin)
    if cfg.get('output_buffer_currents'):
        power['output_buffers_w']=1.8*sum(integral(t,wave[name],begin,end) for name in cfg['output_buffer_currents'])/(end-begin)
        power['total_with_buffers_w']=power['VDD_w']+power['VREFP_w']+power['VCM_w']
        power['total_without_output_buffers_w']=power['total_with_buffers_w']-power['output_buffers_w']
    widths=[b-starts[bisect.bisect_right(starts,b)-1] for b in selected]
    metrics=dict(sample_count=len(codes),invalid_bits=invalid,incomplete_conversions=incomplete,
        comparison_count_errors=count_errors,code_mismatches=mismatches,
        period_error_s=max(abs(b-a-period) for a,b in zip(selected,selected[1:])),
        sample_window_min_s=min(widths),sample_window_max_s=max(widths),
        timing_margin_min_s=min(margins) if margins else -1,
        step_node_error_max_v=max(errors) if errors else 1e9)
    if spec is not None:metrics['sndr_db']=spec['sndr_db']
    if not cfg.get('behavioral_alignment'):
        metrics.pop('code_mismatches')
        metrics['decision_errors_far_boundary']=far_errors
    if physical:
        soa_warnings=len(re.findall(r'WARNING \(CMI-275[1-6]\)',(raw.parent/'logs/spectre.log').read_text()))
        metrics.update(step_diff_error_rms_v=math.sqrt(sum(e*e for e in diff_errors)/len(diff_errors)),
            wrong_bottom_states=switch_errors,output_capture_errors=code_capture_errors,
            output_hold_errors=hold_errors,
            evaluation_count_errors=eval_count_errors,monotonic_switch_errors=monotonic_errors,
            bootstrap_gate_at_first_eval_max_v=max(gate_at_start),first_evaluate_delay_min_s=min(first_eval_delays),
            soa_warning_count=soa_warnings)
    trace_start=starts[bisect.bisect_right(starts,selected[0])-1]
    trace_stop=starts[bisect.bisect_right(starts,selected[0])]
    left=bisect.bisect_left(t,trace_start);right=bisect.bisect_right(t,trace_stop)
    timing={name:wave[name][left:right] for name in ('I_adc.Sample','I_adc.ClkC','I_adc.Valid','EOC','I_adc.Vp','I_adc.Vn','D9','D0')}
    timing['time']=t[left:right]
    return dict(metrics=metrics,codes=codes,conversions=details,bit_traces=traces,spectrum=spec,power=power,
        timing_trace=timing,physical_reference=({'initial_state':'observed top plates before first evaluation',**physical_ref} if physical else None),
        power_convention='Delivered power = -Vsource * I(positive terminal); VSS/VREFN at 0 V deliver zero power')

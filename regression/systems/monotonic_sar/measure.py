"""Observe real output codes and comparator handshakes without driving the DUT."""
import bisect
import cmath
import math
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
    done=edges(t,wave['EOC'],.9,1)
    discard=cfg['discard_cycles'];n=cfg['n'];period=cfg['expected_period_s']
    selected=ends[discard:discard+n]
    if len(selected)!=n:raise ValueError('Insufficient consecutive sampling events: '+str(len(selected)))
    codes=[];invalid=incomplete=count_errors=mismatches=far_errors=0;details=[];traces=[];errors=[];margins=[]
    for index,end in enumerate(selected):
        read=end+cfg['read_offset_s'];code=0
        for bit in range(cfg['bits']):
            v=interpolate(t,wave['D'+str(bit)],read)
            if v>=cfg['logic_high_v']:code|=1<<bit
            elif v>cfg['logic_low_v']:invalid+=1
        stop=starts[bisect.bisect_right(starts,end)]
        valid_times=completes[bisect.bisect_right(completes,end):bisect.bisect_left(completes,stop)]
        done_times=done[bisect.bisect_right(done,end):bisect.bisect_left(done,stop)]
        if len(done_times)!=1 or done_times[0]>=read:incomplete+=1
        else:margins.append(stop-done_times[0])
        count_errors+=int(len(valid_times)!=cfg['bits'])
        vp=interpolate(t,wave['Vinp'],end);vn=interpolate(t,wave['Vinn'],end)
        expected=min(1023,max(0,math.floor(((vp-vn)+1.8)/3.6*1024)))
        mismatches+=int(code!=expected)
        codes.append(code);details.append(dict(index=index,sample_time_s=end,read_time_s=read,code=code,expected=expected,comparisons=len(valid_times),eoc=done_times))
        rp,rn=vp,vn
        for j,when in enumerate(valid_times):
            ap=interpolate(t,wave['I_adc.Vp'],when);an=interpolate(t,wave['I_adc.Vn'],when)
            decision=int(interpolate(t,wave['I_adc.Outp'],when+5e-12)>=.9)
            ideal=int(rp>=rn)
            far_errors+=int(decision!=ideal and abs(rp-rn)>.5*cfg['lsb_v'])
            traces.append(dict(sample=index,bit=9-j,time_s=when,vp=ap,vn=an,diff=ap-an,cm=(ap+an)/2,decision=decision,ideal_diff=rp-rn,ideal_cm=(rp+rn)/2))
            errors.extend([abs(ap-rp),abs(an-rn)])
            if j<9:
                delta=1.8/(2**(j+1))
                if (ideal if cfg.get('behavioral_alignment') else decision):rp-=delta
                else:rn-=delta
    fs=(len(selected)-1)/(selected[-1]-selected[0])
    fin=float(case['condition']['tokens']['FIN']);k=round(fin*n/fs)
    spec=fft_codes(codes,fs,k)
    power={}
    begin=selected[0];end=begin+n/fs
    for supply,voltage in [('VDD',1.8),('VREFP',1.8),('VCM',.9)]:
        power[supply+'_w']=-voltage*integral(t,wave[supply+':p'],begin,end)/(end-begin)
    power['clock_input_w']=-integral(t,[a*b for a,b in zip(wave['Clks'],wave['Vclock:p'])],begin,end)/(end-begin)
    widths=[b-starts[bisect.bisect_right(starts,b)-1] for b in selected]
    metrics=dict(sample_count=len(codes),invalid_bits=invalid,incomplete_conversions=incomplete,
        comparison_count_errors=count_errors,code_mismatches=mismatches,
        period_error_s=max(abs(b-a-period) for a,b in zip(selected,selected[1:])),
        sndr_db=spec['sndr_db'],sample_window_min_s=min(widths),sample_window_max_s=max(widths),
        timing_margin_min_s=min(margins) if margins else -1,
        step_node_error_max_v=max(errors) if errors else 1e9)
    if not cfg.get('behavioral_alignment'):
        metrics.pop('code_mismatches')
        metrics['decision_errors_far_boundary']=far_errors
    return dict(metrics=metrics,codes=codes,conversions=details,bit_traces=traces,spectrum=spec,power=power,
        power_convention='Delivered power = -Vsource * I(positive terminal); VSS/VREFN at 0 V deliver zero power')

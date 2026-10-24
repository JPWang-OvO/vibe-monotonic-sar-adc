import bisect
import math
import cmath
from regression.common.psf import read_psf,interpolate
from .measure import edges,fft_codes,integral

def measure_comparator(case,raw):
    w=read_psf(raw/'tran.tran.tran');t=w['time'];cfg=case['measurement']
    valid=edges(t,w['Valid'],.9,1)
    wrong=missing=reset_errors=0;delays=[];biases=[];details=[]
    for j,point in enumerate(cfg['points']):
        start=cfg['start_s']+j*cfg['period_s']
        found=[v for v in valid if start<=v<start+3.5e-9]
        if len(found)!=1:missing+=1;continue
        done=found[0];delay=done-start;delays.append(delay)
        op=interpolate(t,w['Outp'],done+100e-12);on=interpolate(t,w['Outn'],done+100e-12)
        decision=op>on
        wrong+=int(decision!=(point['differential_v']>0))
        reset_at=start-300e-12
        reset_errors+=int(interpolate(t,w['Outp'],reset_at)<1.62 or interpolate(t,w['Outn'],reset_at)<1.62 or interpolate(t,w['Valid'],reset_at)>.18)
        bias=interpolate(t,w['Bias'],start);biases.append(bias)
        details.append(dict(index=j,**point,delay_s=delay,bias_v=bias,decision=int(decision),tail_v=interpolate(t,w['I_cmp.Tail'],done),bias_drain_v=interpolate(t,w['I_cmp.BiasDrain'],done)))
    return dict(metrics=dict(wrong_decisions=wrong,missing_valid=missing,reset_errors=reset_errors,
        delay_max_s=max(delays) if delays else 1,bias_min_v=min(biases) if biases else 0,bias_max_v=max(biases) if biases else 2),comparisons=details)

def measure_phase(case,raw):
    w=read_psf(raw/'tran.tran.tran');t=w['time']
    rises=[v for v in edges(t,w['Sample'],.9,1) if 200e-9<v<580e-9]
    falls=edges(t,w['Sample'],.9,-1)
    widths=[next(f for f in falls if f>r)-r for r in rises]
    periods=[b-a for a,b in zip(rises,rises[1:])]
    return dict(metrics=dict(pulse_count=len(rises),period_error_s=max([abs(p-20e-9) for p in periods] or [1]),
        width_min_s=min(widths or [0]),width_max_s=max(widths or [1])),rises_s=rises,widths_s=widths,
        por_ramp_final_v=w['I_phase.PorRamp'][-1])

def measure_sampler(case,raw):
    w=read_psf(raw/'tran.tran.tran');t=w['time'];cfg=case['measurement']
    details=[];errs=[];hold=[];gate=[]
    for j,p in enumerate(cfg['points']):
        end=64.01e-9+j*40e-9
        sample={k:interpolate(t,w[k],end-100e-12) for k in ['Vinp','Vinn','Vp','Vn']}
        held={k:interpolate(t,w[k],end+2e-9) for k in ['Vp','Vn']}
        late={k:interpolate(t,w[k],end+15e-9) for k in ['Vp','Vn']}
        error=(held['Vp']-held['Vn'])-(sample['Vinp']-sample['Vinn']);errs.append(error)
        hold.append((late['Vp']-late['Vn'])-(held['Vp']-held['Vn']))
        gate.append(interpolate(t,w['Gp'],end-500e-12)-p)
        details.append(dict(input_p_v=p,tracking_error_diff_v=(sample['Vp']-sample['Vn'])-(sample['Vinp']-sample['Vinn']),hold_error_diff_v=error,held=held))
    return dict(metrics=dict(sample_error_max_v=max(map(abs,errs)),hold_drift_max_v=max(map(abs,hold)),
        bootstrap_min_v=min(gate),bootstrap_max_v=max(gate)),points=details,
        signal_ranges={k:[min(v),max(v)] for k,v in w.items() if k!='time'})

def measure_sampler_sine(case,raw):
    w=read_psf(raw/'tran.tran.tran');t=w['time'];cfg=case['measurement'];n=cfg['n']
    ends=edges(t,w['Sample'],.9,-1)[cfg['discard_cycles']:cfg['discard_cycles']+n]
    if len(ends)!=n:raise ValueError('Sampler did not supply the fixed contiguous window')
    values=[];inputs=[];drift=[]
    for end in ends:
        at=end+cfg['read_offset_s']
        value=interpolate(t,w['Vp'],at)-interpolate(t,w['Vn'],at);values.append(value)
        inputs.append(interpolate(t,w['Vinp'],end)-interpolate(t,w['Vinn'],end))
        drift.append(interpolate(t,w['Vp'],end+14e-9)-interpolate(t,w['Vn'],end+14e-9)-value)
    fs=(n-1)/(ends[-1]-ends[0]);fin=float(case['condition']['tokens']['FIN']);k=round(fin*n/fs)
    spectrum=fft_codes(values,fs,k)
    phasor=lambda v:sum(x*cmath.exp(-2j*math.pi*k*i/n) for i,x in enumerate(v))/n
    response=phasor(values)/phasor(inputs)
    return dict(metrics=dict(sample_count=n,sndr_db=spectrum['sndr_db'],hold_feedthrough_max_v=max(map(abs,drift)),
        period_error_s=max(abs(b-a-20e-9) for a,b in zip(ends,ends[1:]))),held_diff_v=values,sample_times_s=ends,
        hold_drift_v=drift,spectrum=spectrum,gain=abs(response),phase_shift_rad=cmath.phase(response),
        phase_equivalent_delay_s=cmath.phase(response)/(2*math.pi*fin),
        vdd_power_w=-1.8*integral(t,w['VDD_SRC:p'],ends[0],ends[0]+n/fs)/(n/fs),
        analysis_note='Raw held voltages; no gain, phase, offset, or code correction is applied to the FFT.')

def measure_cdac(case,raw):
    w=read_psf(raw/'tran.tran.tran');t=w['time'];cfg=case['measurement'];rows=[];settling=[]
    for j,trace in enumerate(cfg['sequences']):
        start=20e-9+j*40e-9
        initial={s:interpolate(t,w['V'+s],start+4.8e-9) for s in ('p','n')}
        data=[]
        for i,step in enumerate(trace[:-1]):
            at=start+5e-9+i*1e-9
            volt={s:interpolate(t,w['V'+s],at+.8e-9) for s in ('p','n')}
            early={s:interpolate(t,w['V'+s],at+.3e-9) for s in ('p','n')}
            settling.extend(abs(volt[s]-early[s]) for s in ('p','n'))
            data.append(dict(bit=step['bit'],side=step['switched_side'],delta=1.8/(2**(i+1)),voltage=volt))
        rows.append(dict(input_p=cfg['points'][j],initial=initial,steps=data))
    # The zero-differential calibration step identifies one physical parasitic
    # charge ratio. All remaining points/steps validate that model parameter.
    cal=rows[2];gain=(cal['initial']['p']-cal['steps'][0]['voltage']['p'])/.9
    errors=[]
    for row in rows:
        predicted=dict(row['initial'])
        for step in row['steps']:
            predicted[step['side']]-=gain*step['delta']
            residual=(step['voltage']['p']-step['voltage']['n'])-(predicted['p']-predicted['n'])
            step['differential_residual_v']=residual;errors.append(residual)
    return dict(metrics=dict(settling_error_max_v=max(settling),nonlinear_residual_rms_v=math.sqrt(sum(v*v for v in errors)/len(errors))),
        charge_gain=gain,top_parasitic_to_cdac_ratio=1/gain-1,rows=rows,
        analysis_note='Physical charge-gain parameter only; this module test does not correct ADC codes or FFT samples.')

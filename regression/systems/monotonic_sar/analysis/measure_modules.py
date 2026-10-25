"""Functional comparator and divider measurements."""
from regression.common.psf import read_psf,interpolate
from .measure import edges


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

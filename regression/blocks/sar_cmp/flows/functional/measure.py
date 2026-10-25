"""Measure this block and apply the functional flow criteria."""
from regression.common.psf import read_psf, interpolate
from regression.common.measure import criterion
from regression.systems.monotonic_sar.analysis.measure import edges


def measure(case,raw):
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
    result = dict(metrics=dict(wrong_decisions=wrong,missing_valid=missing,reset_errors=reset_errors,
        delay_max_s=max(delays) if delays else 1,bias_min_v=min(biases) if biases else 0,bias_max_v=max(biases) if biases else 2),comparisons=details)
    checks = {name: criterion(result['metrics'][name], rule)
              for name, rule in case['criteria'].items()}
    result.update(checks=checks, functional_pass=all(checks.values()), performance_pass=None)
    return result

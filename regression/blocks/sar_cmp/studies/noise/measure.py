"""Standalone clocked-comparator transient-noise probability measurement."""
import bisect
import math

from regression.common.psf import read_psf, interpolate
from regression.systems.monotonic_sar.analysis.measure import edges, integral
from .stimulus import trial_points


def fit_probability(rows):
    """Binomial maximum likelihood for P(Outp high)=Phi((Vin-offset)/sigma).

    Work in mV for numerical conditioning. Report fit-domain boundaries rather
    than interpreting an unresolved transition as a noise estimate.
    """
    points=[(r['differential_v']*1e3,r['ones'],r['resolved']) for r in rows]
    if sum(0 < k < n for _,k,n in points) < 2:
        return dict(identifiable=False,reason='Fewer than two partially populated probability levels')
    def loss(mu, log_sigma):
        sigma=math.exp(log_sigma);total=0.0
        for x,k,n in points:
            p=min(1-1e-14,max(1e-14,.5*math.erfc(-(x-mu)/sigma/math.sqrt(2))))
            total-=k*math.log(p)+(n-k)*math.log1p(-p)
        return total
    def minimize(fn,lo,hi):
        ratio=(math.sqrt(5)-1)/2
        a=hi-ratio*(hi-lo);b=lo+ratio*(hi-lo);fa=fn(a);fb=fn(b)
        for _ in range(65):
            if fa<fb:hi,b,fb=b,a,fa;a=hi-ratio*(hi-lo);fa=fn(a)
            else:lo,a,fa=a,b,fb;b=lo+ratio*(hi-lo);fb=fn(b)
        return (lo+hi)/2
    mu=0.;ls=math.log(.7);mu_bounds=(-4.,4.);ls_bounds=(math.log(.03),math.log(5.))
    for _ in range(30):
        old=(mu,ls)
        mu=minimize(lambda v:loss(v,ls),*mu_bounds)
        ls=minimize(lambda v:loss(mu,v),*ls_bounds)
        if max(abs(mu-old[0]),abs(ls-old[1]))<1e-8:break
    interior=min(mu-mu_bounds[0],mu_bounds[1]-mu,ls-ls_bounds[0],ls_bounds[1]-ls)>1e-5
    h=1e-3;f=loss(mu,ls)
    aa=(loss(mu+h,ls)-2*f+loss(mu-h,ls))/h**2
    bb=(loss(mu,ls+h)-2*f+loss(mu,ls-h))/h**2
    ab=(loss(mu+h,ls+h)-loss(mu+h,ls-h)-loss(mu-h,ls+h)+loss(mu-h,ls-h))/(4*h*h)
    det=aa*bb-ab*ab
    out=dict(identifiable=interior,offset_v=mu*1e-3,sigma_v=math.exp(ls)*1e-3,negative_log_likelihood=f,
             fit_bounds=dict(offset_mv=list(mu_bounds),sigma_mv=[.03,5.]))
    if interior and det>0:
        out['offset_standard_error_v']=math.sqrt(bb/det)*1e-3
        out['sigma_standard_error_v']=math.exp(ls)*math.sqrt(aa/det)*1e-3
    out['uncertainty_note']='Local binomial Hessian; assumes independent trials and excludes mismatch and inter-cycle noise correlation.'
    return out


def measure(case, raw):
    w=read_psf(raw/'tran.tran.tran');t=w['time'];cfg=case['measurement']
    points=trial_points(cfg['sequence'])
    valid=edges(t,w['Valid'],.9,1);rows={};delays=[];unresolved=reset_errors=valid_late=0
    for j,point in enumerate(points):
        start=cfg['start_s']+j*cfg['period_s'];deadline=start+cfg['decision_time_s']
        cm,diff=point['common_mode_v'],point['differential_v'];key=(cm,diff)
        row=rows.setdefault(key,dict(common_mode_v=cm,differential_v=diff,trials=0,resolved=0,ones=0,unresolved=0,valid_late=0))
        row['trials']+=1
        op=interpolate(t,w['Outp'],deadline);on=interpolate(t,w['Outn'],deadline)
        state=interpolate(t,w['Valid'],deadline)
        resolved=(op>=1.62 and on<=.18) or (on>=1.62 and op<=.18)
        row['valid_late']+=int(state<1.62);valid_late+=int(state<1.62)
        row['resolved']+=int(resolved);row['ones']+=int(resolved and op>on)
        row['unresolved']+=int(not resolved);unresolved+=int(not resolved)
        reset=start-300e-12
        reset_errors+=int(interpolate(t,w['Outp'],reset)<1.62 or interpolate(t,w['Outn'],reset)<1.62 or interpolate(t,w['Valid'],reset)>.18)
        ix=bisect.bisect_left(valid,start)
        if ix<len(valid) and valid[ix]<start+cfg['period_s']/2:delays.append(valid[ix]-start)
    curves=[]
    for cm in sorted({key[0] for key in rows},reverse=True):
        data=sorted([v for (c,d),v in rows.items() if c==cm],key=lambda r:r['differential_v'])
        fit=fit_probability(data);fit['all_decisions_resolved']=not any(r['unresolved'] for r in data)
        curves.append(dict(common_mode_v=cm,points=data,fit=fit))
    start=cfg['start_s'];stop=start+(len(points)-1)*cfg['period_s']
    power=-1.8*integral(t,w['VDD_SRC:p'],start,stop)/(stop-start)
    result = dict(metrics=dict(trials=len(points),unresolved=unresolved,valid_late=valid_late,reset_errors=reset_errors,
                delay_max_s=max(delays) if delays else None,average_supply_power_w=power),curves=curves,
                decision_time_s=cfg['decision_time_s'],loads_f=cfg['loads_f'],
                measurement_scope='Comparator and actual bias circuit with ideal driven inputs/clock and explicit output loads; no ADC, CDAC, sampling noise, or device mismatch.',
                validity_note='Noise probabilities use complementary output rails. Valid below 1.62 V at the deadline is counted separately; delay_max_s is the Valid 0.9 V crossing before reset. Nonzero unresolved or reset errors require review.')
    result.update(checks={}, functional_pass=True, performance_pass=None,
                  performance_scope='Standalone noise characterization; no added ADC acceptance threshold')
    return result

"""Measure this block and apply the functional flow criteria."""
from regression.common.psf import read_psf, interpolate
from regression.common.measure import criterion
from regression.systems.monotonic_sar.analysis.measure import edges


def measure(case,raw):
    w=read_psf(raw/'tran.tran.tran');t=w['time']
    rises=[v for v in edges(t,w['Sample'],.9,1) if 200e-9<v<580e-9]
    falls=edges(t,w['Sample'],.9,-1)
    widths=[next(f for f in falls if f>r)-r for r in rises]
    periods=[b-a for a,b in zip(rises,rises[1:])]
    result = dict(metrics=dict(pulse_count=len(rises),period_error_s=max([abs(p-20e-9) for p in periods] or [1]),
        width_min_s=min(widths or [0]),width_max_s=max(widths or [1])),rises_s=rises,widths_s=widths,
        por_ramp_final_v=w['I_phase.PorRamp'][-1])
    checks = {name: criterion(result['metrics'][name], rule)
              for name, rule in case['criteria'].items()}
    result.update(checks=checks, functional_pass=all(checks.values()), performance_pass=None)
    return result

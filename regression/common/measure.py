"""Measurement dispatch; acceptance thresholds belong to each flow."""
from __future__ import annotations

import math
from pathlib import Path



def criterion(value, rule):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return False
    return (("min" not in rule or value >= rule["min"])
            and ("max" not in rule or value <= rule["max"]))


def measure(case, raw):
    raw = Path(raw)
    cfg = case["measurement"]
    kind = cfg["kind"]
    if kind == 'sar_comparator_noise':
        from regression.systems.monotonic_sar.analysis.measure_cmp_noise import measure_comparator_noise
        result=measure_comparator_noise(case,raw)
        result.update(checks={},functional_pass=True,performance_pass=None,
                      performance_scope='Standalone noise characterization; no added ADC acceptance threshold')
        return result
    if kind in ('sar_comparator','sar_phase'):
        from regression.systems.monotonic_sar.analysis import measure_modules
        result=getattr(measure_modules, 'measure_'+kind[4:])(case,raw)
        checks={name:criterion(result['metrics'][name],rule) for name,rule in case['criteria'].items()}
        result.update(checks=checks,functional_pass=all(checks.values()),performance_pass=None)
        return result
    if kind == "sar":
        from regression.systems.monotonic_sar.analysis.measure import measure_sar
        result = measure_sar(case, raw)
        checks = {name: criterion(result['metrics'][name], rule) for name, rule in case['criteria'].items()}
        result.update(checks=checks, functional_pass=all(checks.values()), performance_pass=checks.get('sndr_db'))
        return result
    raise ValueError('Unknown measurement kind: '+kind)

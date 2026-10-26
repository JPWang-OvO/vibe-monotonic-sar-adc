"""Measurement dispatch; acceptance thresholds belong to each flow."""
from __future__ import annotations

import math
from importlib import import_module
from pathlib import Path


MEASUREMENT_MODULES = {
    'sar': 'regression.systems.monotonic_sar.flows.acceptance.measure',
    'sar_comparator': 'regression.blocks.sar_cmp.flows.functional.measure',
    'sar_phase': 'regression.blocks.sar_phase.flows.functional.measure',
    'sar_comparator_noise': 'regression.blocks.sar_cmp.studies.noise.measure',
}

def criterion(value, rule):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return False
    return (("min" not in rule or value >= rule["min"])
            and ("max" not in rule or value <= rule["max"]))


def measure(case, raw, *, log_path=None):
    kind = case['measurement']['kind']
    if kind not in MEASUREMENT_MODULES:
        raise ValueError('Unknown measurement kind: '+kind)
    module = import_module(MEASUREMENT_MODULES[kind])
    if kind == 'sar':
        return module.measure(case, Path(raw), log_path=log_path)
    return module.measure(case, Path(raw))

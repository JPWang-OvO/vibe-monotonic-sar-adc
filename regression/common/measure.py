"""Small teaching measurements; acceptance thresholds belong to each flow."""
from __future__ import annotations

import math
from pathlib import Path

from regression.common.psf import read_psf, interpolate


def criterion(value, rule):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return False
    return (("min" not in rule or value >= rule["min"])
            and ("max" not in rule or value <= rule["max"]))


def measure(case, raw):
    raw = Path(raw)
    cfg = case["measurement"]
    kind = cfg["kind"]
    metrics = {}
    if kind in ('sar_comparator','sar_phase','sar_sampler','sar_sampler_sine','sar_cdac'):
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
    if kind == "rc_response":
        ac = read_psf(raw / "ac.ac", "freq")
        maximum = 0.0
        tau = cfg["resistance_ohm"] * cfg["capacitance_f"]
        for freq, vout in zip(ac["freq"], ac["OUT"]):
            expected = 1 / complex(1, 2 * math.pi * freq * tau)
            maximum = max(maximum, abs(vout - expected))
        tran = read_psf(raw / "tran.tran.tran")
        # Exact response to a finite linear ramp from 0 to 1 V.
        ramp = cfg["rise_s"]
        errors = []
        for t in cfg["sample_times_s"]:
            elapsed = t - cfg["delay_s"]
            expected = 1 - tau / ramp * math.expm1(ramp / tau) * math.exp(-elapsed / tau)
            errors.append(abs(interpolate(tran["time"], tran["OUT"], t) - expected))
        metrics = {"ac_max_complex_error_v": maximum, "tran_max_error_v": max(errors)}
    elif kind == "inverter":
        tran = read_psf(raw / "tran.tran.tran")
        low, high = [], []
        for row in cfg["samples"]:
            value = interpolate(tran["time"], tran["OUT"], row["time_s"])
            (high if row["expected"] else low).append(value)
        metrics = {"vol_max_v": max(low), "voh_min_v": min(high)}
        dc = read_psf(raw / "dc.dc", "dc")
        metrics["dc_low_input_output_v"] = dc["OUT"][0]
        metrics["dc_high_input_output_v"] = dc["OUT"][-1]
    elif kind == "counter_sequence":
        tran = read_psf(raw / "tran.tran.tran")
        mismatches, invalid = 0, 0
        details = []
        for row in cfg["samples"]:
            code = 0
            for bit, signal in enumerate(cfg["signals_lsb_first"]):
                value = interpolate(tran["time"], tran[signal], row["time_s"])
                if value >= cfg["logic_high_v"]:
                    code |= 1 << bit
                elif value > cfg["logic_low_v"]:
                    invalid += 1
            mismatches += int(code != row["expected"])
            details.append({"time_s": row["time_s"], "expected": row["expected"], "actual": code})
        metrics = {"mismatches": mismatches, "invalid_bits": invalid,
                   "sample_count": len(cfg["samples"])}
    else:
        raise ValueError("Unknown measurement kind: " + kind)
    checks = {name: criterion(metrics[name], rule) for name, rule in case["criteria"].items()}
    result = {"metrics": metrics, "checks": checks, "functional_pass": all(checks.values()),
              "performance_pass": None, "performance_scope": "Not specified for these teaching flows"}
    if kind == "counter_sequence":
        result["events"] = details
    return result

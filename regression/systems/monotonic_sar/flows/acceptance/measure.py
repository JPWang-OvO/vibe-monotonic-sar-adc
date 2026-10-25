"""Measure the ADC and apply this flow's resolved case criteria."""
from regression.common.measure import criterion
from regression.systems.monotonic_sar.analysis.measure import measure_sar


def measure(case, raw):
    result = measure_sar(case, raw)
    checks = {name: criterion(result['metrics'][name], rule)
              for name, rule in case['criteria'].items()}
    result.update(checks=checks, functional_pass=all(checks.values()),
                  performance_pass=checks.get('sndr_db'))
    return result

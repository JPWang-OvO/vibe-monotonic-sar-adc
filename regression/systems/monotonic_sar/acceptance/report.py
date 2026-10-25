"""Evaluate collected batches against a flow; write a candidate report to artifacts."""
import argparse
from pathlib import Path

from regression.common.project import ROOT, read_json, write_json
from regression.common.plans import load_plan
from regression.common.measure import criterion


def report(flow_path, batches):
    flow_path = Path(flow_path).resolve()
    flow = load_plan(flow_path)
    expected = {c['id']: c for c in flow['conditions']}
    rows = []
    seen = set()
    reference = None
    source_equal = True
    for folder in map(Path, batches):
        batch = read_json(folder/'batch.json')
        settings = {c['id']: c for c in batch['cases']}
        for result in read_json(folder/'summary.json')['cases']:
            case = settings[result['case']]
            if case['flow'] != flow_path.relative_to(ROOT).as_posix():
                continue
            condition = case['condition']['id']
            if condition not in expected or condition in seen:
                raise ValueError('Unexpected or duplicate condition: '+condition)
            contract = expected[condition]
            assert case['condition'] == contract, condition
            assert case['measurement'] == flow['measurement'], condition
            assert case['criteria'] == contract['criteria'], condition
            assert case['simulator'] == flow['simulator'], condition
            seen.add(condition)
            inputs = folder/'cases'/case['id']/'inputs'
            source = {name: (inputs/name).read_text(encoding='utf-8')
                      for name in case['sources']['sources'] if name != case['sources']['entry']}
            if reference is None:
                reference = source
            else:
                source_equal &= source == reference
            metrics = result.get('metrics', {})
            checks = {name: criterion(metrics.get(name), rule) for name, rule in contract['criteria'].items()}
            passed = bool(result['execution_pass'] and result['log_audit']['pass']
                          and result['measurement_pass'] and all(checks.values()))
            rows.append(dict(condition=condition, batch=folder.name, case=case['id'], passed=passed,
                             metrics=metrics, checks=checks, power=result.get('power')))
    return dict(flow=flow_path.relative_to(ROOT).as_posix(),
                all_electrical_pass=seen == set(expected) and source_equal and all(r['passed'] for r in rows),
                dut_sources_equal=source_equal, required_cases=len(expected), completed_cases=len(rows),
                passed_cases=sum(r['passed'] for r in rows), cases=rows,
                missing_conditions=sorted(set(expected)-seen), status='candidate_report')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flow', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('batches', type=Path, nargs='+')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT):
        parser.error('Candidate reports belong outside the source repository; baseline promotion requires review')
    result = report(args.flow, args.batches)
    write_json(args.output, result)
    print(f'{result["passed_cases"]}/{result["required_cases"]} passed; {args.output}')


if __name__ == '__main__':
    main()

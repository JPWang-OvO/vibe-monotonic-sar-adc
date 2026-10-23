"""Measure completed server waveforms again without launching a simulator."""
import argparse
from pathlib import Path
from regression.common.project import read_json, write_json
from regression.common.measure import measure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    batch = read_json(args.batch/'batch.json')
    execution = read_json(args.batch/'summary.json')
    cases = {case['id']:case for case in batch['cases']}
    reports = []
    for original in execution['cases']:
        if original['execution_pass'] and original['log_audit']['pass']:
            result = measure(cases[original['case']], Path(original['remote_waveforms']))
            reports.append({'case':original['case'], **result})
    write_json(args.output, {'batch_id':batch['batch_id'], 'data_processing':'server',
        'waveforms_downloaded':False, 'cases':reports})


if __name__=='__main__':
    main()

"""Summarize a study batch by parameter point without promoting a baseline."""
import argparse
from pathlib import Path

from regression.common.project import ROOT, read_json, write_json


def summarize(folder):
    folder=Path(folder)
    batch=read_json(folder/'batch.json')
    results={r['case']:r for r in read_json(folder/'summary.json')['cases']}
    plans={c['flow'] for c in batch['cases']}
    if len(plans)!=1 or not next(iter(plans)).endswith('/study.json'):
        raise ValueError('Select a batch from one study')
    study=read_json(ROOT/next(iter(plans)))
    objective=study['objective'].get('minimize')
    groups={}
    for case in batch['cases']:
        parameters=case['condition']['study_parameters']
        key=tuple(sorted(parameters.items()))
        group=groups.setdefault(key,dict(parameters=parameters,cases=[],complete=True,feasible=True,values=[]))
        result=results.get(case['id'])
        group['cases'].append(case['id'])
        group['complete'] &= result is not None and bool(result.get('measurement_pass'))
        group['feasible'] &= result is not None and bool(result.get('pass'))
        if objective and result and result.get('measurement_pass'):
            group['values'].append(result['metrics'][objective])
    rows=[]
    for group in groups.values():
        values=group.pop('values')
        group['worst_objective']=max(values) if objective and group['complete'] else None
        rows.append(group)
    if objective:
        rows.sort(key=lambda r:(not r['feasible'],r['worst_objective'] is None,r['worst_objective']))
    return dict(study=next(iter(plans)),objective=study['objective'],ranking_scope='Cases selected in this batch; maximum metric over each parameter point',
                points=rows,batch=str(folder.resolve()),status='study_results')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('batch',type=Path);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.resolve().is_relative_to(ROOT):
        p.error('Study results belong outside the source repository')
    write_json(args.output,summarize(args.batch));print(args.output)


if __name__=='__main__':main()

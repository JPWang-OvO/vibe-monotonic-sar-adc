"""Collect saved measurements after cancellation or a confirmed controller exit."""
import json
from pathlib import Path

root=Path.cwd()
state=json.loads((root/'status.json').read_text())
assert state['state'] in ('cancelled','controller_error'),state
assert not list(root.glob('cases/*/active.json')),'Simulator cancellation is not complete'
if (root/'summary.json').exists():
    print('Preserved existing controller summary')
    raise SystemExit(0)
batch=json.loads((root/'batch.json').read_text())
reports=[];unfinished=[]
for case in batch['cases']:
    path=root/'cases'/case['id']/'results.json'
    if path.exists():reports.append(json.loads(path.read_text()))
    else:unfinished.append(case['id'])
summary=dict(batch_id=batch['batch_id'],cases=reports,not_run=unfinished,
             passed_cases=sum(bool(r.get('pass')) for r in reports),
             **{'pass':not unfinished and all(r.get('pass') for r in reports)},
             state=state['state'],data_processing='server',waveforms_downloaded=False)
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(dict(completed=len(reports),unfinished=unfinished)))

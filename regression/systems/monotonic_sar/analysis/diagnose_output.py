"""Measure output settling relative to EOC and the fixed read time."""
import argparse,json,sys,shlex
from pathlib import Path
from regression.common.project import read_json
from inspect import getsource
from regression.systems.monotonic_sar.analysis.measure import edges
from regression.common.runner import ssh,checked


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch",type=Path)
    parser.add_argument("case")
    args=parser.parse_args()
    folder=args.batch;case_id=args.case;batch=read_json(folder/'batch.json');runner=ssh(batch)
    script='''import json,bisect
from pathlib import Path
from regression.common.psf import read_psf,interpolate
MEASUREMENT_HELPERS
r=json.loads(Path('cases/'+CASE+'/results.json').read_text());w=read_psf(Path('cases/'+CASE+'/raw/tran.tran.tran'));t=w['time'];rows=[]
crossings={(b,high):edges(t,w['D'+str(b)],1.62 if high else .18,1 if high else -1) for b in range(10) for high in (False,True)}
for c in r['conversions']:
 end=c['sample_time_s'];done=c['eoc'][0];target=c['decision_code'];read=c['read_time_s'];settles=[]
 for b in range(10):
  values=w['D'+str(b)];high=bool(target&(1<<b));level=1.62 if high else .18
  v=interpolate(t,values,done)
  at=done if (v>=level if high else v<=level) else crossings[b,high][bisect.bisect_right(crossings[b,high],done)]
  settles.append(at)
 rows.append(dict(index=c['index'],done_after_sample_ns=(done-end)*1e9,settled_after_sample_ns=(max(settles)-end)*1e9,settle_after_done_ns=(max(settles)-done)*1e9,read_margin_ns=(read-max(settles))*1e9))
print(json.dumps(rows))
'''.replace('CASE',repr(case_id))
    script=script.replace("MEASUREMENT_HELPERS","import cmath, math\n"+getsource(edges))
    local=folder/(case_id+'_output_diagnostic.py');local.write_text(script,encoding='utf-8',newline='\n');checked(runner.upload(local,batch['remote']+'/'+local.name))
    result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],local.name]),timeout=90))
    (folder/(case_id+'_output_diagnostic.json')).write_text(result,encoding='utf-8')
    rows=json.loads(result)
    print(dict(conversions=len(rows),minimum_read_margin_ns=min(r['read_margin_ns'] for r in rows),
               maximum_settling_ns=max(r['settle_after_done_ns'] for r in rows),
               late=[r for r in rows if r['read_margin_ns']<0]))


if __name__ == "__main__":
    main()

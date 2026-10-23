"""Read the saved floating-node and wait-gate output terminal voltages."""
import sys,shlex
from pathlib import Path
from regression.common.project import read_json
from regression.common.runner import ssh,checked
folder=Path(sys.argv[1]);case_id=sys.argv[2];batch=read_json(folder/'batch.json');runner=ssh(batch)
script='''import json
from pathlib import Path
from regression.common.psf import read_psf,interpolate
w=read_psf(Path('cases/'+CASE+'/raw/tran.tran.tran'));t=w['time']
p=w['I_adc.I_async.I_run_nor.P2'];z=w['I_adc.I_async.CompareEnable']
vds=[a-b for a,b in zip(z,p)];result={}
for name,values in [('P2',p),('Z',z),('Vds',vds)]:
 lo=min(range(len(t)),key=values.__getitem__);hi=max(range(len(t)),key=values.__getitem__)
 result[name]=dict(min_v=values[lo],min_time_ns=t[lo]*1e9,max_v=values[hi],max_time_ns=t[hi]*1e9)
r=json.loads(Path('cases/'+CASE+'/results.json').read_text())
result['first_conversion']=[]
for row in r['bit_traces']:
 if row['sample']!=0:continue
 at=row['evaluate_time_s']
 result['first_conversion'].append(dict(bit=row['bit'],evaluate_ns=at*1e9,P2=interpolate(t,p,at),Z=interpolate(t,z,at),Delayed=interpolate(t,w['I_adc.I_async.ValidDelay'],at),Early=interpolate(t,w['I_adc.I_async.Early'],at)))
print(json.dumps(result))
'''.replace('CASE',repr(case_id))
local=folder/(case_id+'_wait_diagnostic.py');local.write_text(script,encoding='utf-8',newline='\n');checked(runner.upload(local,batch['remote']+'/'+local.name))
result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],local.name]),timeout=90))
(folder/(case_id+'_wait_diagnostic.json')).write_text(result,encoding='utf-8');print(result)

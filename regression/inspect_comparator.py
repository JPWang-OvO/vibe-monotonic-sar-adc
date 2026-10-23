"""Read comparator internal voltages on the server; transfer numeric samples only."""
import json,sys,shlex
from pathlib import Path
from regression.common.runner import ssh,checked
from regression.common.project import read_json

folder=Path(sys.argv[1]);batch=read_json(folder/'batch.json');runner=ssh(batch)
script='''import json
from pathlib import Path
from regression.common.psf import read_psf,interpolate
from regression.systems.monotonic_sar.measure import edges
w=read_psf(Path('cases/sar_cmp__tt/raw/tran.tran.tran'));t=w['time']
r=[]
for j in range(20):
    at=52.01e-9+j*10e-9
    r.append(dict(index=j,samples=[dict(dt_ns=dt,**{k:interpolate(t,v,at+dt*1e-9) for k,v in w.items() if k!='time'}) for dt in (0,1,2,3.5)]))
print(json.dumps(r))
'''
local=folder/'diagnostic.py';local.write_text(script,encoding='utf-8',newline='\n')
checked(runner.upload(local,batch['remote']+'/diagnostic.py'))
result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],'diagnostic.py']),timeout=30))
(folder/'diagnostic.json').write_text(result,encoding='utf-8')
for row in json.loads(result):
    s=row['samples'][-1]
    print(row['index'],{k:round(v,5) for k,v in s.items() if k in ('Vp','Vn','Outp','Outn','Valid','I_cmp.Xp','I_cmp.Xn','I_cmp.Tail','I_cmp.BiasDrain')})

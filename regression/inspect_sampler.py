"""Transfer a sparse sampler diagnostic after processing server PSF."""
import json,sys,shlex
from pathlib import Path
from regression.common.runner import ssh,checked
from regression.common.project import read_json
folder=Path(sys.argv[1]);batch=read_json(folder/'batch.json');runner=ssh(batch)
script='''import json
from pathlib import Path
from regression.common.psf import read_psf,interpolate
w=read_psf(Path('cases/sar_sampler__tt/raw/tran.tran.tran'));t=w['time'];r=[]
for j in range(5):
 at=60.01e-9+j*40e-9
 r.append(dict(index=j,samples=[dict(dt_ns=dt,**{k:interpolate(t,w[k],at+dt*1e-9) for k in ['Vinp','Vinn','Vp','Vn','I_sp.Cb','I_sp.Ct','I_sp.Gate','I_sn.Cb','I_sn.Gate']}) for dt in (-1,0,1,2,3,3.8,4,4.2,5,6)]))
print(json.dumps(r))
'''
local=folder/'diagnostic.py';local.write_text(script,encoding='utf-8',newline='\n');checked(runner.upload(local,batch['remote']+'/diagnostic.py'))
result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],'diagnostic.py']),timeout=30))
(folder/'sampler_diagnostic.json').write_text(result,encoding='utf-8')
for row in json.loads(result):
 print('point',row['index'])
 for s in row['samples']:print({k:round(v,5) for k,v in s.items()})

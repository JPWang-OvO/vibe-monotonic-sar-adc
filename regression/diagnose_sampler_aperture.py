"""Inspect existing sampler waveforms; these diagnostics do not alter acceptance."""
import json,sys,shlex
from pathlib import Path
from regression.common.runner import ssh,checked
from regression.common.project import read_json
folder=Path(sys.argv[1]);batch=read_json(folder/'batch.json');runner=ssh(batch)
script='''import json,bisect
from pathlib import Path
from regression.common.psf import read_psf,interpolate
from regression.systems.monotonic_sar.measure import edges,fft_codes
w=read_psf(Path('cases/sar_sampler_sine__k51/raw/tran.tran.tran'));t=w['time']
ends=edges(t,w['Sample'],.9,-1)[16:272];r=[]
for dt in (-.3,-.1,0,.05,.1,.15,.2,.3,.5,1):
 vals=[interpolate(t,w['Vp'],e+dt*1e-9)-interpolate(t,w['Vn'],e+dt*1e-9) for e in ends]
 f=fft_codes(vals,255/(ends[-1]-ends[0]),51)
 r.append(dict(offset_ns=dt,sndr_db=f['sndr_db'],h3_power=f['power'][103]))
points=[]
for e in ends[:12]:
 points.append(dict(sample_end=e,trace=[dict(dt_ns=dt,**{k:interpolate(t,w[k],e+dt*1e-9) for k in ('Vinp','Vinn','Vp','Vn','Gp','Gn','SampleB')}) for dt in (-.2,0,.05,.1,.15,.2,.3,.5)]))
print(json.dumps(dict(spectra=r,points=points)))
'''
local=folder/'aperture_diagnostic.py';local.write_text(script,encoding='utf-8',newline='\n');checked(runner.upload(local,batch['remote']+'/'+local.name))
result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],local.name]),timeout=90))
(folder/'aperture_diagnostic.json').write_text(result,encoding='utf-8');r=json.loads(result)
print(json.dumps(r['spectra'],indent=2));print(json.dumps(r['points'][:3],indent=2))

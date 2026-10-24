"""Inspect existing sampler waveforms; these diagnostics do not alter acceptance."""
import argparse,json,sys,shlex
from pathlib import Path
from regression.common.runner import ssh,checked
from regression.common.project import read_json
from inspect import getsource
from regression.systems.monotonic_sar.analysis.measure import edges,fft_codes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch",type=Path)
    parser.add_argument("case")
    args=parser.parse_args()
    folder=args.batch;batch=read_json(folder/'batch.json');runner=ssh(batch)
    case_id=args.case
    script='''import json,bisect
from pathlib import Path
from regression.common.psf import read_psf,interpolate
MEASUREMENT_HELPERS
w=read_psf(Path('cases/'+CASE_ID+'/raw/tran.tran.tran'));t=w['time']
ends=edges(t,w['Sample'],.9,-1)[16:272];r=[]
for dt in (-.3,-.1,0,.05,.1,.15,.2,.3,.5,1):
 vals=[interpolate(t,w['Vp'],e+dt*1e-9)-interpolate(t,w['Vn'],e+dt*1e-9) for e in ends]
 f=fft_codes(vals,255/(ends[-1]-ends[0]),51)
 r.append(dict(offset_ns=dt,sndr_db=f['sndr_db'],h3_power=f['power'][103]))
points=[]
for e in ends[:12]:
 points.append(dict(sample_end=e,trace=[dict(dt_ns=dt,**{k:interpolate(t,w[k],e+dt*1e-9) for k in ('Vinp','Vinn','Vp','Vn','Gp','Gn','SampleB')}) for dt in (-.2,0,.05,.1,.15,.2,.3,.5)]))
off=[]
for key in ('Gp','Gn'):
 falls=edges(t,w[key],.2,-1)
 off.extend(next(v for v in falls if e<v<e+2e-9)-e for e in ends)
print(json.dumps(dict(spectra=r,points=points,gate_reset_delay_min_s=min(off),gate_reset_delay_max_s=max(off))))
'''.replace('CASE_ID',repr(case_id))
    script=script.replace("MEASUREMENT_HELPERS","import cmath, math\n"+getsource(edges)+"\n"+getsource(fft_codes))
    local=folder/'aperture_diagnostic.py';local.write_text(script,encoding='utf-8',newline='\n');checked(runner.upload(local,batch['remote']+'/'+local.name))
    result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],local.name]),timeout=90))
    (folder/'aperture_diagnostic.json').write_text(result,encoding='utf-8');r=json.loads(result)
    print(json.dumps(r['spectra'],indent=2));print('gate_reset_delay_s',r['gate_reset_delay_min_s'],r['gate_reset_delay_max_s']);print(json.dumps(r['points'][:1],indent=2))


if __name__ == "__main__":
    main()

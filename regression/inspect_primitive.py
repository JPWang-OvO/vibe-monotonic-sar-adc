from pathlib import Path
import json,shlex
from virtuoso_bridge.env import load_vb_env
from virtuoso_bridge.transport.tunnel import SSHClient

ROOT=Path(__file__).resolve().parents[1]
load_vb_env(explicit=str(ROOT.parent.parent/'Virtuoso Bridge/.env'))
env=json.loads((ROOT/'config/environments/tsmc18.local.json').read_text())
runner=SSHClient.from_env(profile=env['profile'],keep_remote_files=True).spectre_runner
out=ROOT/'artifacts/primitive_inspection';out.mkdir(parents=True,exist_ok=True)
remote=env['remote_runs']+'/primitive_inspection'
def check(r):
    if r.returncode:raise RuntimeError(r.stderr or r.stdout)
    return r.stdout+r.stderr
print(check(runner.run_command('command -v python3')))
print(check(runner.run_command('python3 --version')))
check(runner.run_command(shlex.join(['mkdir',remote])))
source='simulator lang=spectre\n'
for s in ('tt_lib','pre_simu'):source+=f'include "{env["model_files"]["tsmc18"]}" section={s}\n'
source+='''subckt test (D G S B)
parameters ww=2u ff=1 mm=1
Mtest (D G S B) nch w=ww l=180n nf=ff m=mm
ends test
Xone (dn gn 0 0) test
Xmulti (dn gn 0 0) test ww=1u ff=4 mm=2
Mp (dp gp vdd vdd) pch w=2u l=180n nf=1 m=1
Vd (dn 0) vsource dc=.9
Vg (gn 0) vsource dc=.9
Vp (dp 0) vsource dc=.9
Vgp (gp 0) vsource dc=.9
VDD (vdd 0) vsource dc=1.8
printOpts options digits=17
instances info what=inst where=file file="instances.txt"
nodes info what=nodes where=file file="nodes.txt"
'''
(out/'inspect.scs').write_text(source,encoding='utf-8',newline='\n')
(out/'inspect.mdl').write_text('run instances\nrun nodes\n',encoding='utf-8',newline='\n')
for name in ('inspect.scs','inspect.mdl'):check(runner.upload(out/name,remote+'/'+name))
cmd=[env['spectre'],'-64','inspect.scs','=mdlcontrol','inspect.mdl','+preset=ax','+mt=8','+log','spectre.log']
r=runner.run_command('cd '+shlex.quote(remote)+' && '+shlex.join(cmd),timeout=60)
(out/'command.log').write_text(r.stdout+r.stderr,encoding='utf-8')
check(r)
for name in ('instances.txt','nodes.txt','spectre.log'):check(runner.download(remote+'/'+name,out/name))
print('Inspection saved: '+str(out))

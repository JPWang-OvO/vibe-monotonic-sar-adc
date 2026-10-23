"""Read remote simulator documentation and allocate this run's isolated directory."""
from pathlib import Path
import json
import shlex
from virtuoso_bridge.env import load_vb_env
from virtuoso_bridge.transport.tunnel import SSHClient

ROOT=Path(__file__).resolve().parents[1]
load_vb_env(explicit=str(ROOT.parent.parent/'Virtuoso Bridge/.env'))
env=json.loads((ROOT/'config/environments/tsmc18.local.json').read_text())
runner=SSHClient.from_env(profile=env['profile'],keep_remote_files=True).spectre_runner
out=ROOT/'artifacts/environment'
out.mkdir(parents=True,exist_ok=True)
def run(args):
    r=runner.run_command(shlex.join(args),timeout=60)
    if r.returncode: raise RuntimeError(r.stderr or r.stdout)
    return r.stdout+r.stderr
run(['mkdir',env['remote_runs']])
for topic in ('info','alter','bsim4','tran'):
    text=run([env['spectre'],'-h',topic])
    (out/(topic+'.txt')).write_text(text,encoding='utf-8')
print(run(['uname','-a']))
print(run(['nproc']))
print(run(['free','-m']))
print('Independent remote directory: '+env['remote_runs'])

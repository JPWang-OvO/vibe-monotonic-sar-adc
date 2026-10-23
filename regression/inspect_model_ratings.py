"""Read installed MOS model rating parameters without altering the PDK."""
import json,shlex,tarfile,shutil
from pathlib import Path
from regression.common.project import ROOT,read_json,artifact_root
from regression.common.runner import ssh,checked
env=read_json(ROOT/'config/environments/tsmc18.local.json');runner=ssh({'environment':env})
out=artifact_root()/'model_ratings';out.mkdir(exist_ok=False);remote=env['remote_runs']+'/model_ratings'
source=env['remote_runs']+'/preparation/pdk_5v_qualification/primitive/source/input.scs'
(out/'ratings.scs').write_text('simulator lang=spectre\ninclude '+json.dumps(source)+'\nmodel_parameters info what=models where=file file="models.txt"\n',encoding='utf-8',newline='\n')
(out/'ratings.mdl').write_text('run model_parameters\n',encoding='utf-8',newline='\n')
checked(runner.run_command(shlex.join(['mkdir',remote])))
for name in ('ratings.scs','ratings.mdl'):checked(runner.upload(out/name,remote+'/'+name))
args=[env['spectre'],'-64','ratings.scs','=mdlcontrol','ratings.mdl','+preset=ax','+mt=8','+log','spectre.log']
checked(runner.run_command('cd '+shlex.quote(remote)+' && '+shlex.join(args),timeout=120))
checked(runner.run_command('cd '+shlex.quote(remote)+' && tar -czf reports.tar.gz models.txt spectre.log',timeout=30))
checked(runner.download(remote+'/reports.tar.gz',out/'reports.tar.gz',timeout=30))
with tarfile.open(out/'reports.tar.gz') as archive:
 for member in archive:
  if not member.isfile() or member.name not in ('models.txt','spectre.log'):raise ValueError('Unexpected report')
  with archive.extractfile(member) as src,(out/member.name).open('wb') as dest:shutil.copyfileobj(src,dest)
for line in (out/'models.txt').read_text().splitlines():
 if line.startswith('Model:') or ('_max' in line and any(key in line for key in ('vgs','vgd','vgb','vds','vbs','vbd'))):print(line)

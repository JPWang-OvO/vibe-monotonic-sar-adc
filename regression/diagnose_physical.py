"""Re-read retained waveforms with detailed step observations, preserving results."""
import json,sys,shlex
from pathlib import Path
from regression.common.runner import ssh,checked
from regression.common.project import ROOT,read_json
folder=Path(sys.argv[1]);case_id=sys.argv[2];batch=read_json(folder/'batch.json');runner=ssh(batch)
script=(ROOT/'regression/systems/monotonic_sar/measure.py').read_text()
script+='\nimport json\nfrom pathlib import Path\ncase_id='+repr(case_id)+'\ncase=json.loads(Path("cases/"+case_id+"/settings.json").read_text())\nr=measure_sar(case,Path("cases/"+case_id+"/raw"))\nprint(json.dumps(r))\n'
local=folder/(case_id+'_physical_diagnostic.py');local.write_text(script,encoding='utf-8',newline='\n');checked(runner.upload(local,batch['remote']+'/'+local.name))
result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],local.name]),timeout=90))
(folder/(case_id+'_physical_diagnostic.json')).write_text(result,encoding='utf-8');r=json.loads(result)
print(r['metrics'])
for v in r['bit_traces'][:10]:print({k:v[k] for k in ['bit','time_s','evaluate_time_s','decision','ideal_diff','before_evaluate_vp','before_evaluate_vn','pending_bottoms']})

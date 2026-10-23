"""Read compact partial results while a large batch or collection is running."""
import json,shlex,sys
from pathlib import Path
from regression.common.project import read_json
from regression.common.runner import ssh,checked

folder=Path(sys.argv[1]);batch=read_json(folder/'batch.json');runner=ssh(batch)
script='''import json
from pathlib import Path
print(json.dumps(json.loads(Path('status.json').read_text())))
for path in sorted(Path('cases').glob('*/results.json')):
    d=json.loads(path.read_text());m=d.get('metrics',{})
    print(json.dumps(dict(case=d['case'],passed=d.get('pass'),execution_pass=d.get('execution_pass'),
        failed_checks=[k for k,v in d.get('checks',{}).items() if not v],
        metrics={k:m.get(k) for k in ['sndr_db','period_error_s','timing_margin_min_s','step_diff_error_rms_v','sample_window_min_s','sample_window_max_s','soa_warning_count']},
        measurement_error=d.get('measurement_error'))))
'''
local=folder/'peek_status.py';local.write_text(script,encoding='utf-8',newline='\n')
checked(runner.upload(local,batch['remote']+'/'+local.name))
print(checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],local.name]),timeout=30)))

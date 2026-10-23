"""Print compact ADC case metrics and distinct warning classes."""
import json,re,sys
from collections import Counter
from pathlib import Path
batch=Path(sys.argv[1]);data=json.loads((batch/'summary.json').read_text())
for case in data['cases']:
    warnings=case.get('log_audit',{}).get('warnings',[])
    counts=Counter(re.search(r'\(([A-Z]+-\d+)\)',line).group(1) for line in warnings if re.search(r'\(([A-Z]+-\d+)\)',line))
    print(json.dumps(dict(case=case['case'],passed=case.get('pass'),execution_pass=case.get('execution_pass'),
        metrics=case.get('metrics'),failed_checks=[k for k,v in case.get('checks',{}).items() if not v],
        warning_counts=dict(counts),errors=case.get('log_audit',{}).get('errors'),
        measurement_error=case.get('measurement_error')),ensure_ascii=False))
print('not_run',data.get('not_run',[]))

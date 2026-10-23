"""Inspect saved transition samples at the largest sampling-period residual."""
import sys,shlex
from pathlib import Path
from regression.common.project import read_json
from regression.common.runner import ssh,checked
folder=Path(sys.argv[1]);case_id=sys.argv[2];batch=read_json(folder/'batch.json');runner=ssh(batch)
script='''import json,bisect,re,subprocess
from pathlib import Path
from regression.common.psf import read_psf
from regression.systems.monotonic_sar.measure import edges
signals=['time','Clks','I_adc.Sample','I_adc.I_phase.Clock','I_adc.I_phase.R0']+['I_adc.I_phase.SampleN'+str(i) for i in range(5)]
source=Path('cases/'+CASE+'/raw/tran.tran.tran');selected=source.parent.parent/'phase_diagnostic.psf'
pattern='^(HEADER|TYPE|SWEEP|TRACE|VALUE|END|[)])$|^"('+'|'.join(re.escape(n) for n in signals)+')"'
with selected.open('w') as out:subprocess.run(['grep','-E',pattern,str(source)],stdout=out,check=True)
w=read_psf(selected);t=w['time'];s=w['I_adc.Sample']
result=json.loads(Path('cases/'+CASE+'/results.json').read_text());ends=[r['sample_time_s'] for r in result['conversions']]
j=max(range(1,len(ends)),key=lambda i:abs(ends[i]-ends[i-1]-20e-9));rows=[]
for at in ends[j-1:j+1]:
 i=bisect.bisect_right(t,at)
 rows.append(dict(crossing_ns=at*1e9,samples=[dict(dt_ps=(t[k]-at)*1e12,Sample=s[k],Clks=w['Clks'][k]) for k in range(i-5,i+5)]))
report=dict(index=j,period_error_ps=(ends[j]-ends[j-1]-20e-9)*1e12,transitions=rows)
if 'I_adc.I_phase.Clock' in w:
 report['phase_nodes']=[]
 for name,direction in [('Clks',1),('I_adc.I_phase.Clock',1),('I_adc.I_phase.R0',-1),('I_adc.I_phase.SampleN0',1),('I_adc.I_phase.SampleN1',-1),('I_adc.I_phase.SampleN2',1),('I_adc.I_phase.SampleN3',-1),('I_adc.I_phase.SampleN4',1),('I_adc.Sample',-1)]:
  es=edges(t,w[name],.9,direction);selected=[es[bisect.bisect_right(es,at+1e-15)-1] for at in ends]
  error=[(b-a-20e-9)*1e12 for a,b in zip(selected,selected[1:])]
  report['phase_nodes'].append(dict(name=name,period_error_max_ps=max(map(abs,error)),period_error_rms_ps=(sum(x*x for x in error)/len(error))**.5,sample_lag_mean_ns=sum(a-b for a,b in zip(ends,selected))/len(ends)*1e9))
print(json.dumps(report))
'''.replace('CASE',repr(case_id))
local=folder/(case_id+'_period_diagnostic.py');local.write_text(script,encoding='utf-8',newline='\n');checked(runner.upload(local,batch['remote']+'/'+local.name))
result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],local.name]),timeout=180))
(folder/(case_id+'_period_diagnostic.json')).write_text(result,encoding='utf-8');print(result)

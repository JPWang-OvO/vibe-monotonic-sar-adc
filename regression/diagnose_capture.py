"""Measure actual sequence, capture and DAC propagation from retained nodes."""
import json,sys,shlex
from pathlib import Path
from regression.common.runner import ssh,checked
from regression.common.project import read_json
folder=Path(sys.argv[1]);case_id=sys.argv[2];batch=read_json(folder/'batch.json');runner=ssh(batch)
script='''import json,bisect
from pathlib import Path
from regression.common.psf import read_psf,interpolate
from regression.systems.monotonic_sar.measure import edges
w=read_psf(Path('cases/'+CASE_ID+'/raw/tran.tran.tran'));t=w['time']
end=edges(t,w['I_adc.Sample'],.9,-1)[16]
valid=[x for x in edges(t,w['I_adc.Valid'],.9,1) if end<x<end+16e-9]
ev=edges(t,w['I_adc.ClkC'],.9,-1);rows=[]
for j,v in enumerate(valid[:9]):
 bit=9-j;side='p' if interpolate(t,w['I_adc.Outp'],v+5e-12)>.9 else 'n';b='I_adc.B'+side+str(bit)
 first=lambda name,level,direction:next(x for x in edges(t,w[name],level,direction) if x>v)
 row=dict(bit=bit,valid_s=v,capture_delay_ns=(first('I_adc.Ck'+str(bit),.9,1)-v)*1e9,evaluate_delay_ns=(next(x for x in ev if x>v)-v)*1e9)
 if 'I_adc.I_async.Raw'+str(bit) in w:row['raw_delay_ns']=(first('I_adc.I_async.Raw'+str(bit),.9,1)-v)*1e9
 for level in (1.62,.9,.18,.0018):row['bottom_'+str(level)+'_delay_ns']=(first(b,level,-1)-v)*1e9
 rows.append(row)
print(json.dumps(rows))
'''.replace('CASE_ID',repr(case_id))
local=folder/(case_id+'_capture_diagnostic.py');local.write_text(script,encoding='utf-8',newline='\n');checked(runner.upload(local,batch['remote']+'/'+local.name))
result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],local.name]),timeout=90))
(folder/(case_id+'_capture_diagnostic.json')).write_text(result,encoding='utf-8')
print(result)

"""Inspect incomplete development runs without changing their acceptance results."""
import json,sys,shlex
from pathlib import Path
from regression.common.runner import ssh,checked
from regression.common.project import read_json
folder=Path(sys.argv[1]);case_id=sys.argv[2];batch=read_json(folder/'batch.json');runner=ssh(batch)
script='''import json,bisect
from pathlib import Path
from regression.common.psf import read_psf,interpolate
from regression.systems.monotonic_sar.measure import edges,fft_codes
case_id=CASE_ID
case=json.loads(Path('cases/'+case_id+'/settings.json').read_text());cfg=case['measurement']
w=read_psf(Path('cases/'+case_id+'/raw/tran.tran.tran'));t=w['time']
ends=edges(t,w['I_adc.Sample'],.9,-1);starts=edges(t,w['I_adc.Sample'],.9,1)
valid=edges(t,w['I_adc.Valid'],.9,1);eoc=edges(t,w['EOC'],.9,1)
selected=ends[cfg['discard_cycles']:cfg['discard_cycles']+cfg['n']]
rows=[];codes=[];invalid=0
for j,end in enumerate(selected):
 at=end+cfg['read_offset_s']
 if at>t[-1]:break
 code=0
 for bit in range(10):
  v=interpolate(t,w['D'+str(bit)],at)
  if v>=cfg['logic_high_v']:code|=1<<bit
  elif v>cfg['logic_low_v']:invalid+=1
 next_start=next((s for s in starts if s>end),t[-1])
 vv=[v for v in valid if end<v<next_start];ee=[v for v in eoc if end<v<next_start]
 codes.append(code);rows.append(dict(index=j,time=end,code=code,comparisons=len(vv),eoc=ee))
report=dict(raw_stop_s=t[-1],sample_ends=len(ends),selected=len(selected),codes=codes,invalid_bits=invalid,rows=rows,
 complete_code_window=len(codes)==256,power_measured=False,diagnostic_only=True)
if len(codes)==256:
 fs=255/(selected[-1]-selected[0]);k=round(float(case['condition']['tokens']['FIN'])*256/fs)
 report['spectrum']=fft_codes(codes,fs,k)
report['first_conversion_trace']=[dict(time=v,**{k:interpolate(t,w[k],v+5e-12) for k in ['I_adc.Vp','I_adc.Vn','I_adc.Outp','I_adc.Outn','I_adc.ClkC']}) for v in valid if selected[0]<v<selected[0]+16e-9]
cr=edges(t,w['I_adc.ClkC'],.9,1);cf=edges(t,w['I_adc.ClkC'],.9,-1);vf=edges(t,w['I_adc.Valid'],.9,-1)
report['loop_timing']=[]
for v in valid:
 if not selected[0]<v<selected[0]+14e-9:continue
 r=next(x for x in cr if x>v);f=next(x for x in cf if x>r);lo=next(x for x in vf if x>v);nxt=next(x for x in valid if x>v)
 report['loop_timing'].append(dict(valid_to_reset_s=r-v,reset_to_valid_low_s=lo-r,valid_low_to_evaluate_s=f-lo,evaluate_to_next_valid_s=nxt-f,period_s=nxt-v))
print(json.dumps(report))
'''.replace('CASE_ID',repr(case_id))
local=folder/(case_id+'_diagnostic.py');local.write_text(script,encoding='utf-8',newline='\n');checked(runner.upload(local,batch['remote']+'/'+local.name))
result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],local.name]),timeout=60))
(folder/(case_id+'_diagnostic.json')).write_text(result,encoding='utf-8');r=json.loads(result)
print({k:v for k,v in r.items() if k not in ('rows','codes','spectrum','first_conversion_trace')})
print('sndr_db',r.get('spectrum',{}).get('sndr_db'));print('comparison counts',sorted(set(row['comparisons'] for row in r['rows'])))
print('first codes',r['codes'][:20]);print('invalid conversion count',sum(row['comparisons']!=10 or len(row['eoc'])!=1 for row in r['rows']))

"""Measure actual sequence, capture and DAC propagation from retained nodes."""
import argparse,json,sys,shlex
from pathlib import Path
from regression.common.runner import ssh,checked
from regression.common.project import read_json
from inspect import getsource
from regression.systems.monotonic_sar.analysis.measure import edges


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch",type=Path)
    parser.add_argument("case")
    args=parser.parse_args()
    folder=args.batch;case_id=args.case;batch=read_json(folder/'batch.json');runner=ssh(batch)
    script='''import json,bisect
from pathlib import Path
from regression.common.psf import read_psf,interpolate
MEASUREMENT_HELPERS
w=read_psf(Path('cases/'+CASE_ID+'/raw/tran.tran.tran'));t=w['time']
end=edges(t,w['I_adc.Sample'],.9,-1)[16]
valid=[x for x in edges(t,w['I_adc.Valid'],.9,1) if end<x<end+16e-9]
ev=edges(t,w['I_adc.ClkC'],.9,-1);rows=[]
for j,v in enumerate(valid[:9]):
 bit=9-j;side='p' if interpolate(t,w['I_adc.Outp'],v+5e-12)>.9 else 'n';b='I_adc.B'+side+str(bit)
 first=lambda name,level,direction:next(x for x in edges(t,w[name],level,direction) if x>v)
 row=dict(bit=bit,valid_s=v,capture_delay_ns=(first('I_adc.Ck'+str(bit),.9,1)-v)*1e9,evaluate_delay_ns=(next(x for x in ev if x>v)-v)*1e9)
 for level in (1.62,.9,.18,.0018):row['bottom_'+str(level)+'_delay_ns']=(first(b,level,-1)-v)*1e9
 rows.append(row)
print(json.dumps(rows))
'''.replace('CASE_ID',repr(case_id))
    script=script.replace("MEASUREMENT_HELPERS","import cmath, math\n"+getsource(edges))
    local=folder/(case_id+'_capture_diagnostic.py');local.write_text(script,encoding='utf-8',newline='\n');checked(runner.upload(local,batch['remote']+'/'+local.name))
    result=checked(runner.run_command('cd '+shlex.quote(batch['remote'])+' && '+shlex.join([batch['environment']['server_python'],local.name]),timeout=90))
    (folder/(case_id+'_capture_diagnostic.json')).write_text(result,encoding='utf-8')
    print(result)


if __name__ == "__main__":
    main()

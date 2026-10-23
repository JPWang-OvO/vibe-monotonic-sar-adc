from fractions import Fraction
from pathlib import Path
import csv
import json
import math
from .model import PARAMS,ROOT,convert,ideal_reference
from .fft import spectrum,validate_known_signals

def main():
    out=ROOT/'artifacts/python_reference'
    out.mkdir(parents=True,exist_ok=True)
    lsb=Fraction(36,10)/1024
    diffs=[Fraction(str(v)) for v in (-1.8,-1.7,-.9,-.1,0,.1,.9,1.7,1.8)]
    # A few selected transitions; this is an algorithm boundary check, not INL/DNL.
    for boundary in (1,255,511,512,513,768,1023):
        for delta in (-Fraction(1,100000),0,Fraction(1,100000)):
            diffs.append(-Fraction(18,10)+(boundary+delta)*lsb)
    fixed=[]
    for d in diffs:
        vp,vn=Fraction(9,10)+d/2,Fraction(9,10)-d/2
        code,trace=convert(vp,vn)
        expected=ideal_reference(d)
        assert code==expected,(d,code,expected)
        assert len(trace)==10
        assert [s['switched_weight'] for s in trace]==PARAMS['weights']+[0]
        assert all(trace[i+1]['common_mode']<=trace[i]['common_mode'] for i in range(9))
        fixed.append(dict(differential=float(d),code=code,expected=expected,trace=trace))
    (out/'fixed_inputs.json').write_text(json.dumps(fixed,indent=2)+'\n')
    results=[]
    for k in PARAMS['fft_bins']:
        codes=[]
        rows=[]
        for sample in range(256):
            t=sample/PARAMS['fs_hz']+PARAMS['sampling_window_s']
            d=1.8*10**(-1/20)*math.sin(2*math.pi*k*PARAMS['fs_hz']/256*t)
            vp,vn=.9+d/2,.9-d/2
            code,trace=convert(vp,vn)
            assert code==ideal_reference(Fraction(str(vp))-Fraction(str(vn)))
            codes.append(code)
            rows.extend(dict(sample=sample,sample_time_s=t,code=code,**s) for s in trace)
        with (out/f'trace_k{k}.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        (out/f'codes_k{k}.json').write_text(json.dumps(codes)+'\n')
        result=spectrum(codes,PARAMS['fs_hz'],k)
        (out/f'spectrum_k{k}.json').write_text(json.dumps(result,indent=2)+'\n')
        assert result['sndr_db']>=PARAMS['sndr_threshold_db'][len(results)]
        results.append(dict(k=k,sndr_db=result['sndr_db'],code_alignment=True))
    summary=dict(fixed_input_count=len(fixed),fft_self_test=validate_known_signals(),sines=results,pass_all=True)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()

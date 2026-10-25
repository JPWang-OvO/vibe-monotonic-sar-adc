"""Check the prepared ADC source boundary and fixed measurement contract."""
import argparse,json,re
from pathlib import Path
from regression.common.project import ROOT,read_json


def main():
    p=argparse.ArgumentParser();p.add_argument('batch',type=Path);p.add_argument('--formal',action='store_true')
    p.add_argument('--acceptance',type=Path,default=ROOT/'regression/systems/monotonic_sar/flows/acceptance/specification.json');a=p.parse_args()
    batch=read_json(a.batch/'batch.json');fixed=read_json(a.acceptance)
    for case in batch['cases']:
        sources=case['sources'];folder=a.batch/'cases'/case['id']/'inputs';supplies=[]
        for name in sources['sources']:
            text='\n'.join(line.split('//')[0] for line in (folder/name).read_text().splitlines())
            assert not re.search(r'\b(?:ahdl_include|bsource|vccs|vcvs|cccs|ccvs|isource|relay|switch)\b',text,re.I),name
            assert not re.search(r'\b(?:errpreset|reltol|vabstol|iabstol|maxstep|cmin|gmin|readic|readns)\s*=',text,re.I),name
            assert not re.search(r'^\s*(?:ic|nodeset)\b',text,re.M|re.I),name
            for match in re.finditer(r'^\s*(\S+)\s*\([^\n]+\)\s+vsource\b',text,re.M):
                assert name==sources['entry'],(name,match.group(1))
                supplies.append(match.group(1))
        assert sorted(supplies)==sorted(['VDD','VSS','VCM','VREFP','VREFN','VinP','VinN','Vclock']),supplies
        assert case['simulator']['arguments']==['-64','+preset=ax']
        assert case['simulator']['threads']==8
        enrichment=case['enrichment']
        assert enrichment['device_count']>0 and enrichment['native_readback_match'] and enrichment['dimensions_preserved'] and enrichment['connectivity_preserved']
        if a.formal:
            cfg=case['measurement'];assert cfg['n']==256 and cfg['fft'] and cfg['physical_frontend']
            for key in ['discard_cycles','read_offset_s','logic_low_v','logic_high_v']:assert cfg[key]==fixed[key],key
        print(json.dumps(dict(case=case['id'],boundary_pass=True,formal=a.formal,source_files=len(sources['sources']),
            ideal_testbench_sources=supplies,inspected_mos_count=enrichment['inspected_mos_count'],cell_views=sources['cell_views'])))


if __name__ == "__main__":
    main()

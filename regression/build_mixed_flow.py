"""Bind an explicit list of verified transistor modules into the timed system."""
import argparse
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js

def main():
    p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('modules',nargs='+');p.add_argument('--smoke',action='store_true');a=p.parse_args()
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/timed/flow.json')
    obj['id']='sar_'+a.name;obj['process']='tsmc18'
    obj['simulator']['timeout_s']=1800
    obj['simulator']['analyses']='Transient 5.80 us, 256 contiguous conversions after 16 startup cycles'
    for c in obj['conditions']:
        c['corner']='tt';c['enrichment']=True
        for module in a.modules:c['cell_views'][module]='transistor'
    obj['measurement']['behavioral_alignment']=False
    obj['criteria'].pop('code_mismatches');obj['criteria'].pop('step_node_error_max_v')
    obj['criteria'].update(decision_errors_far_boundary={'max':0},timing_margin_min_s={'min':2e-9})
    if a.smoke:
        tb='library/testbenches/systems/monotonic_sar/tb_SAR_smoke'
        write(tb+'/spectre/netlist.scs',(ROOT/obj['testbench']).read_text().replace('stop=5.80u','stop=1.20u'))
        js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_smoke',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
        obj['testbench']=tb+'/spectre/netlist.scs';obj['measurement'].update(n=32,fft=False)
        obj['criteria']['sample_count']={'min':32,'max':32};obj['criteria'].pop('sndr_db')
        obj['simulator']['analyses']='Development functional/timing smoke: 32 conversions after 16 startup cycles; no FFT acceptance'
        obj['simulator']['timeout_s']=600
    f='regression/systems/monotonic_sar/flows/'+a.name
    js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

if __name__=='__main__':main()

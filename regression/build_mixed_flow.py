"""Bind an explicit list of verified transistor modules into the timed system."""
import argparse
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js

def main():
    p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('modules',nargs='+');a=p.parse_args()
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/timed/flow.json')
    obj['id']='sar_'+a.name;obj['process']='tsmc18'
    for c in obj['conditions']:
        c['corner']='tt';c['enrichment']=True
        for module in a.modules:c['cell_views'][module]='transistor'
    obj['measurement']['behavioral_alignment']=False
    obj['criteria'].pop('code_mismatches');obj['criteria'].pop('step_node_error_max_v')
    obj['criteria'].update(decision_errors_far_boundary={'max':0},timing_margin_min_s={'min':2e-9})
    f='regression/systems/monotonic_sar/flows/'+a.name
    js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

if __name__=='__main__':main()

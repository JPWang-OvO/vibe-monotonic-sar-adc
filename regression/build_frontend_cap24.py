"""Reduce the measured SS junction residual by a 20% CDAC increase."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
for mode in ('static','sine','loaded'):
    obj=read_json(ROOT/f'regression/blocks/sar_frontend/flows/refined_{mode}/flow.json');obj['id']='sar_frontend_cap24_'+mode
    for c in obj['conditions']:
        c['cell_views']['SAR_SAMPLE']='junction384'
        if mode=='loaded':c['tokens']['CUNIT']='24f'
        else:c['tokens']['CLOAD']='12.288p'
    f='regression/blocks/sar_frontend/flows/cap24_'+mode;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

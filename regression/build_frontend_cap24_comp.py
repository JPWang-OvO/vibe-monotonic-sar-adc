"""Retune gate-charge cancellation after the measured CDAC load change."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
tb='library/testbenches/blocks/dac/tb_SAR_CDAC_cap24'
source=(ROOT/'library/testbenches/blocks/dac/tb_SAR_CDAC_loaded/spectre/netlist.scs').read_text().replace('ccross=34f','ccross=28f')
write(tb+'/spectre/netlist.scs',source);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_CDAC_cap24',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
for mode in ('static','sine','loaded'):
    obj=read_json(ROOT/f'regression/blocks/sar_frontend/flows/cap24_{mode}/flow.json');obj['id']='sar_frontend_cap24c28_'+mode
    if mode=='loaded':obj['testbench']=tb+'/spectre/netlist.scs'
    else:
        for c in obj['conditions']:c['tokens']['CCOMP']='28f'
    f='regression/blocks/sar_frontend/flows/cap24c28_'+mode;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

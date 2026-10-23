"""Remove two output-driver stages from the completion detection path."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/comparator/SAR_CMP'
s=(ROOT/(base+'/fast3/netlist.scs')).read_text().replace('I_valid (Outp Outn ValidRaw','I_valid (Np0 Nn0 ValidRaw')
write(base+'/fast4/netlist.scs',s)
meta=read_json(ROOT/(base+'/cell.json'));meta['views']['fast4']={'netlist':'fast4/netlist.scs'};js(base+'/cell.json',meta)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/control_fast3/flow.json');obj['id']='sar_control_fast4'
for c in obj['conditions']:c['cell_views']['SAR_CMP']='fast4'
f='regression/systems/monotonic_sar/flows/control_fast4';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

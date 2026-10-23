"""Clock output registers from the tenth completion before buffered EOC."""
import re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/systems/monotonic_sar/MONOTONIC_SAR';s=(ROOT/(base+'/spectre/netlist.scs')).read_text()
s,count=re.subn(r'(I_out\d+ \(Q\d+) EOC ',r'\1 Ck0 ',s);assert count==10
write(base+'/early_save/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['early_save']={'netlist':'early_save/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_pullup/flow.json');obj['id']='sar_physical_early_save'
for c in obj['conditions']:c['cell_views']['MONOTONIC_SAR']='early_save'
f='regression/systems/monotonic_sar/flows/physical_early_save';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

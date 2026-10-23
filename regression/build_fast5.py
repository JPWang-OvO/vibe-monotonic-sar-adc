"""Reset promptly while retaining time for captured data and DAC switching."""
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
save('logic','SAR_HANDSHAKE_SKEW',['A','Z','VDD','VSS'],
    mos('Mn0','N0 A VSS VSS','nch',4)+mos('Mp0','N0 A VDD VDD','pch',1)+
    mos('Mn1','Z N0 VSS VSS','nch',4)+mos('Mp1','Z N0 VDD VDD','pch',16))
base='library/blocks/control/SAR_ASYNC'
s=(ROOT/(base+'/fast3/netlist.scs')).read_text().replace('SAR_HANDSHAKE','SAR_HANDSHAKE_SKEW')
write(base+'/fast5/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['fast5']={'netlist':'fast5/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/control_fast4/flow.json');obj['id']='sar_control_fast5'
for c in obj['conditions']:c['cell_views']['SAR_ASYNC']='fast5'
f='regression/systems/monotonic_sar/flows/control_fast5';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

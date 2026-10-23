"""Capture an already settled comparison with a transparent-then-hold latch."""
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
body=mos('Mn_h','HoldB Hold VSS VSS','nch',1)+mos('Mp_h','HoldB Hold VDD VDD','pch',2)
body+=mos('Mn_in','N HoldB D VSS','nch',1)+mos('Mp_in','N Hold D VDD','pch',2)
body+=mos('Mn_fb','N Hold Q VSS','nch',1)+mos('Mp_fb','N HoldB Q VDD','pch',2)
body+=mos('Mn_qb','QB N VSS VSS','nch',1)+mos('Mp_qb','QB N VDD VDD','pch',2)
body+=mos('Mn_q','Q QB VSS VSS','nch',1)+mos('Mp_q','Q QB VDD VDD','pch',2)
save('logic','SAR_CAPTURE_LATCH',['D','Hold','Q','QB','VDD','VSS'],body)
base='library/blocks/control/SAR_BIT';s=(ROOT/(base+'/fast6/netlist.scs')).read_text()
s=s.replace('include "../../../../support/standard_cells/DFQD1BWP7T/spectre/netlist.scs"','include "../../../logic/SAR_CAPTURE_LATCH/transistor/netlist.scs"')
s=s.replace('I_latch (Outp Capture Q VDD VSS) DFQD1BWP7T\nI_qbar (Q QB VDD VSS) INVD1BWP7T\nI_capture_delay (Capture CaptureD VDD VSS) SAR_DELAY2','I_latch (Outp Capture Q QB VDD VSS) SAR_CAPTURE_LATCH')
s=s.replace('Q CaptureD','Q Capture').replace('QB CaptureD','QB Capture')
s=s.replace('include "../../../../support/standard_cells/INVD1BWP7T/spectre/netlist.scs"\n','').replace('include "../../../logic/SAR_DELAY2/transistor/netlist.scs"\n','')
write(base+'/latch/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['latch']={'netlist':'latch/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/control_fast7/flow.json');obj['id']='sar_control_latch'
for c in obj['conditions']:c['cell_views']['SAR_BIT']='latch'
f='regression/systems/monotonic_sar/flows/control_latch';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

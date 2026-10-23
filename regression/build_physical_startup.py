"""Arm conversion only after the first sample and wait for bootstrap reset."""
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
old='library/blocks/logic/SAR_SAMPLE_GUARD'
s=(ROOT/(old+'/transistor/netlist.scs')).read_text().replace('SAR_SAMPLE_GUARD','SAR_SAMPLE_GUARD12')
s=s.replace('I_d7 (N6 Delayed VDD VSS) INVD1BWP7T',
    'I_d7 (N6 N7 VDD VSS) INVD1BWP7T\nI_d8 (N7 N8 VDD VSS) INVD1BWP7T\nI_d9 (N8 N9 VDD VSS) INVD1BWP7T\nI_d10 (N9 N10 VDD VSS) INVD1BWP7T\nI_d11 (N10 Delayed VDD VSS) INVD1BWP7T')
base='library/blocks/logic/SAR_SAMPLE_GUARD12';write(base+'/transistor/netlist.scs',s)
m=read_json(ROOT/(old+'/cell.json'));m['cell']='SAR_SAMPLE_GUARD12';js(base+'/cell.json',m)
body=mos('Mp_charge','PorRamp VSS VDD VDD','pch',.36,l=5)+'C_por (PorRamp VSS) capacitor c=200f\n'
body+='I_por0 (PorRamp Por VDD VSS) INVD1BWP7T\nI_por1 (Por PorN VDD VSS) INVD1BWP7T\n'
body+='I_arm (VDD Sample PorN Ready VDD VSS) SAR_DFFR\nI_ready_inv (Ready NotReady VDD VSS) SAR_DRIVE scale=1\n'
body+=mos('Mn0','HoldN Guard VSS VSS','nch',2)+mos('Mn1','HoldN NotReady VSS VSS','nch',2)
body+=mos('Mp0','P0 Guard VDD VDD','pch',4)+mos('Mp1','HoldN NotReady P0 VDD','pch',4)
body+='I_hold (HoldN Hold VDD VSS) SAR_DRIVE scale=1\nI_sample_inv (Sample SampleB VDD VSS) SAR_DRIVE scale=1\nI_clear (Ready SampleB ClearB VDD VSS) SAR_NAND2\nI_clear_drive (ClearB ClearN VDD VSS) SAR_DRIVE scale=8\n'
save('logic','SAR_STARTUP',['Sample','Guard','Hold','ClearN','VDD','VSS'],body,
    'include "../../../../support/standard_cells/INVD1BWP7T/spectre/netlist.scs"\ninclude "../../../logic/SAR_DFFR/transistor/netlist.scs"\ninclude "../../../logic/SAR_DRIVE/transistor/netlist.scs"\ninclude "../../../logic/SAR_NAND2/transistor/netlist.scs"\n')
base='library/blocks/control/SAR_ASYNC';s=(ROOT/(base+'/fast7/netlist.scs')).read_text().replace('SAR_SAMPLE_GUARD','SAR_SAMPLE_GUARD12')
s=s.replace('subckt SAR_ASYNC','include "../../../logic/SAR_STARTUP/transistor/netlist.scs"\nsubckt SAR_ASYNC')
s=s.replace('I_sample_inv (Sample ClearN VDD VSS) SAR_DRIVE scale=8','I_startup (Sample SampleGuard Hold ClearN VDD VSS) SAR_STARTUP')
s=s.replace('(SampleGuard Valid ValidDelay Ck0 CompareEnable','(Hold Valid ValidDelay Ck0 CompareEnable')
write(base+'/startup/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['startup']={'netlist':'startup/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_smoke/flow.json');obj['id']='sar_physical_startup'
for c in obj['conditions']:c['cell_views'].update(SAR_ASYNC='startup',SAR_BIT='latch')
f='regression/systems/monotonic_sar/flows/physical_startup';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

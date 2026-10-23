"""Retain the fast precharged wait gate while damping its measured overshoot."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/logic/SAR_WAIT_GATE';s=(ROOT/(base+'/transistor/netlist.scs')).read_text().replace('ends SAR_WAIT_GATE','C_stack (P2 VDD) capacitor c=15f\nends SAR_WAIT_GATE')
write(base+'/damped/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['damped']={'netlist':'damped/netlist.scs'};js(base+'/cell.json',m)
old='library/blocks/logic/SAR_SAMPLE_GUARD12';base='library/blocks/logic/SAR_SAMPLE_GUARD10'
s=(ROOT/(old+'/transistor/netlist.scs')).read_text().replace('SAR_SAMPLE_GUARD12','SAR_SAMPLE_GUARD10')
s=s.replace('I_d9 (N8 N9 VDD VSS) INVD1BWP7T\nI_d10 (N9 N10 VDD VSS) INVD1BWP7T\nI_d11 (N10 Delayed VDD VSS) INVD1BWP7T','I_d9 (N8 Delayed VDD VSS) INVD1BWP7T')
write(base+'/transistor/netlist.scs',s);m=read_json(ROOT/(old+'/cell.json'));m['cell']='SAR_SAMPLE_GUARD10';js(base+'/cell.json',m)
base='library/blocks/control/SAR_ASYNC';s=(ROOT/(base+'/weighted4/netlist.scs')).read_text().replace('SAR_SAMPLE_GUARD12','SAR_SAMPLE_GUARD10')
write(base+'/weighted4_fast/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['weighted4_fast']={'netlist':'weighted4_fast/netlist.scs'};js(base+'/cell.json',m)
old='library/blocks/logic/SAR_DFFR';base='library/blocks/logic/SAR_ARM'
s=(ROOT/(old+'/transistor/netlist.scs')).read_text().replace('SAR_DFFR','SAR_ARM').replace('C_storage (net5 VSS) capacitor c=3f','C_storage (net5 VSS) capacitor c=5f')
write(base+'/transistor/netlist.scs',s);m=read_json(ROOT/(old+'/cell.json'));m['cell']='SAR_ARM';m['views']={'transistor':{'netlist':'transistor/netlist.scs'}};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_STARTUP';s=(ROOT/(base+'/quiet/netlist.scs')).read_text().replace('SAR_DFFR','SAR_ARM')
write(base+'/quiet_arm/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['quiet_arm']={'netlist':'quiet_arm/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_out_buffered/flow.json');obj['id']='sar_physical_damped'
for c in obj['conditions']:c['cell_views'].update(SAR_ASYNC='weighted4_fast',SAR_WAIT_GATE='damped',SAR_STARTUP='quiet_arm')
f='regression/systems/monotonic_sar/flows/physical_damped';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

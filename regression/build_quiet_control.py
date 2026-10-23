"""Remove measured stack-node overshoot and reduce sample-edge modulation."""
from regression.build_transistors import mos
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/clock/SAR_PHASE';s=(ROOT/(base+'/drive4/netlist.scs')).read_text();s=s[:s.index('I_buffer0')]
for i,scale in enumerate((1,4,16,128)):
    s+=f'I_buffer{i} ({"R0" if i==0 else "SampleN"+str(i-1)} SampleN{i} VDD VSS) SAR_DRIVE scale={scale}\n'
for i in range(2):s+=f'I_pre{i} (SampleN3 SampleN4 VDD VSS) SAR_DRIVE scale=512\n'
for i in range(16):s+=f'I_final{i} (SampleN4 Sample VDD VSS) SAR_DRIVE scale=512\n'
s+='ends SAR_PHASE\n';write(base+'/drive8k/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['drive8k']={'netlist':'drive8k/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_STARTUP';s=(ROOT/(base+'/ordered/netlist.scs')).read_text()
body=mos('Mn_clear0','ClearB SampleB ClearX VSS','nch',2)+mos('Mn_clear1','ClearX Ready VSS VSS','nch',2)
body+=mos('Mp_clear0','ClearB Ready VDD VDD','pch',2)+mos('Mp_clear1','ClearB SampleB VDD VDD','pch',2)
s=s.replace('I_clear (Ready SampleB ClearB VDD VSS) SAR_NAND2\n',body)
write(base+'/quiet/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['quiet']={'netlist':'quiet/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_WAIT_GATE';s=(ROOT/(base+'/transistor/netlist.scs')).read_text()
s=s.replace('Mp_delay (P2 Delayed P1','Mp_delay (Z Delayed P2').replace('Mp_early (P2 Early P1','Mp_early (Z Early P2').replace('Mp_valid (Z Valid P2','Mp_valid (P2 Valid P1')
write(base+'/ordered/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['ordered']={'netlist':'ordered/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_early_save/flow.json');obj['id']='sar_physical_quiet'
for c in obj['conditions']:c['cell_views'].update(SAR_PHASE='drive8k',SAR_STARTUP='quiet',SAR_WAIT_GATE='ordered')
obj['criteria']['soa_warning_count']={'max':0}
f='regression/systems/monotonic_sar/flows/physical_quiet';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

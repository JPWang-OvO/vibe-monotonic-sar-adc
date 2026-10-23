"""Give Valid a direct reset path and retain delayed release of reset."""
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
body=''
for i,a in enumerate(('A','B','C','D')):
    body+=mos('Mn'+str(i),f'Z {a} VSS VSS','nch',4)
    body+=mos('Mp'+str(i),f'{"P"+str(i) if i<3 else "Z"} {a} {"VDD" if i==0 else "P"+str(i-1)} VDD','pch',24)
save('logic','SAR_NOR4',['A','B','C','D','Z','VDD','VSS'],body)
body=''
for i in range(4):body+=f'I_d{i} ({"A" if i==0 else "N"+str(i-1)} N{i} VDD VSS) INVD1BWP7T\n'
body+='I_d4 (N3 N4 VDD VSS) SAR_DRIVE scale=1\nI_d5 (N4 Z VDD VSS) SAR_DRIVE scale=4\n'
save('logic','SAR_DONE_DELAY',['A','Z','VDD','VSS'],body,
    'include "../../../../support/standard_cells/INVD1BWP7T/spectre/netlist.scs"\ninclude "../../../logic/SAR_DRIVE/transistor/netlist.scs"\n')
base='library/blocks/control/SAR_ASYNC'
s=(ROOT/(base+'/fast3/netlist.scs')).read_text().replace('SAR_DELAY4','SAR_SAMPLE_GUARD').replace('SAR_NOR3','SAR_NOR4')
s=s.replace('(SampleGuard ValidDelay Ck0 CompareEnable','(SampleGuard Valid ValidDelay Ck0 CompareEnable')
s=s.replace('SAR_DELAY/transistor','SAR_DONE_DELAY/transistor').replace(' SAR_DELAY\n',' SAR_DONE_DELAY\n')
write(base+'/fast7/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['fast7']={'netlist':'fast7/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/control_fast6/flow.json');obj['id']='sar_control_fast7'
for c in obj['conditions']:c['cell_views']['SAR_ASYNC']='fast7'
f='regression/systems/monotonic_sar/flows/control_fast7';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

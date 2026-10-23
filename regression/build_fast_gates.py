"""Size the demonstrated reset/handshake bottlenecks for their actual fanout."""
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
body=''
for i,a in enumerate(('A','B','C')):
    body+=mos('Mn'+str(i),f'Z {a} VSS VSS','nch',2)
    body+=mos('Mp'+str(i),f'{"P"+str(i) if i<2 else "Z"} {a} {"VDD" if i==0 else "P"+str(i-1)} VDD','pch',18)
save('logic','SAR_NOR3',['A','B','C','Z','VDD','VSS'],body)
body=mos('Mn0','Z A N0 VSS','nch',2)+mos('Mn1','N0 B VSS VSS','nch',2)
body+=mos('Mp0','Z A VDD VDD','pch',2)+mos('Mp1','Z B VDD VDD','pch',2)
save('logic','SAR_NAND2',['A','B','Z','VDD','VSS'],body)
save('logic','SAR_INV_SMALL',['A','Z','VDD','VSS'],mos('Mn','Z A VSS VSS','nch',1)+mos('Mp','Z A VDD VDD','pch',2))
def view(base,source):
    write(base+'/fast2/netlist.scs',source);meta=read_json(ROOT/(base+'/cell.json'));meta['views']['fast2']={'netlist':'fast2/netlist.scs'};js(base+'/cell.json',meta)
base='library/blocks/control/SAR_ASYNC'
s=(ROOT/(base+'/fast/netlist.scs')).read_text()
s=s.replace('../../../../support/standard_cells/NR3D1BWP7T/spectre/netlist.scs','../../../logic/SAR_NOR3/transistor/netlist.scs').replace('NR3D1BWP7T','SAR_NOR3')
s=s.replace('I_clock_drive (CompareEnable ClkC VDD VSS) SAR_DRIVE scale=1','I_clock_drive (CompareEnable ClkC VDD VSS) SAR_DRIVE scale=4');view(base,s)
base='library/blocks/control/SAR_BIT';s=(ROOT/(base+'/transistor/netlist.scs')).read_text()
s=s.replace('SAR_DELAY4','SAR_DELAY2').replace('../../../../support/standard_cells/ND2D1BWP7T/spectre/netlist.scs','../../../logic/SAR_NAND2/transistor/netlist.scs').replace('ND2D1BWP7T','SAR_NAND2');view(base,s)
base='library/blocks/comparator/SAR_CMP';s=(ROOT/(base+'/transistor/netlist.scs')).read_text()
s=s.replace('Mn_reset_p (Xp ClkC VSS VSS) nch w=4u','Mn_reset_p (Xp ClkC VSS VSS) nch w=8u').replace('Mn_reset_n (Xn ClkC VSS VSS) nch w=4u','Mn_reset_n (Xn ClkC VSS VSS) nch w=8u')
s=s.replace('I_outp (Xp Outp VDD VSS) INVD1BWP7T','I_outp (Xp Outp VDD VSS) SAR_INV_SMALL').replace('I_outn (Xn Outn VDD VSS) INVD1BWP7T','I_outn (Xn Outn VDD VSS) SAR_INV_SMALL')
s=s.replace('../../../../support/standard_cells/INVD1BWP7T/spectre/netlist.scs','../../../logic/SAR_INV_SMALL/transistor/netlist.scs')
s=s.replace('../../../../support/standard_cells/ND2D1BWP7T/spectre/netlist.scs','../../../logic/SAR_NAND2/transistor/netlist.scs').replace('ND2D1BWP7T','SAR_NAND2');view(base,s)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/control_fast/flow.json');obj['id']='sar_control_fast2'
for c in obj['conditions']:c['cell_views'].update(SAR_CMP='fast2',SAR_ASYNC='fast2',SAR_BIT='fast2')
f='regression/systems/monotonic_sar/flows/control_fast2';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

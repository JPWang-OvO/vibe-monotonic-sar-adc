"""Test higher comparison current and reset strength against the SS delay limit."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/comparator/SAR_CMP';s=(ROOT/(base+'/fast4/netlist.scs')).read_text()
s=s.replace('pch w=24u l=0.36u nf=3','pch w=48u l=0.36u nf=6').replace('pch w=24u l=0.18u nf=3','pch w=48u l=0.18u nf=6')
s=s.replace('Mn_reset_p (Xp ClkC VSS VSS) nch w=4u','Mn_reset_p (Xp ClkC VSS VSS) nch w=8u').replace('Mn_reset_n (Xn ClkC VSS VSS) nch w=4u','Mn_reset_n (Xn ClkC VSS VSS) nch w=8u')
write(base+'/current/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['current']={'netlist':'current/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/blocks/sar_cmp/flows/extended3/flow.json');obj['id']='sar_cmp_current'
for c in obj['conditions']:c['cell_views']['SAR_CMP']='current'
f='regression/blocks/sar_cmp/flows/current';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

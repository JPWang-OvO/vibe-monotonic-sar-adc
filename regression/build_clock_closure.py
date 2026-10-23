"""Use observed Clock feedthrough to select a stronger, damped clock driver."""
import re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/clock/SAR_PHASE'
s=(ROOT/(base+'/clock8/netlist.scs')).read_text().replace('SAR_DRIVE scale=4\nMn_clock','SAR_DRIVE scale=8\nMn_clock')
s=s.replace('nch w=4u l=0.72u','nch w=8u l=0.72u').replace('pch w=8u l=0.72u','pch w=16u l=0.72u').replace('c=240f','c=320f')
write(base+'/clock16/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['clock16']={'netlist':'clock16/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_SAMPLE_GUARD2'
s=(ROOT/(base+'/quiet20/netlist.scs')).read_text().replace('c=20f','c=15f')
write(base+'/quiet15/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['quiet15']={'netlist':'quiet15/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_OUTPUT_FF'
s=(ROOT/(base+'/fast2/netlist.scs')).read_text()
for name,width in [('Mn_cp',2),('Mp_cp',4)]:s=re.sub(r'('+name+r' .*?)w=\S+',rf'\1w={width}u',s)
write(base+'/fast3/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['fast3']={'netlist':'fast3/netlist.scs'};js(base+'/cell.json',m)
for group in ('slow','corners'):
    obj=read_json(ROOT/f'regression/systems/monotonic_sar/flows/physical_pvt_closure_{group}/flow.json');obj['id']='sar_clock16_'+group
    for c in obj['conditions']:c['cell_views'].update(SAR_PHASE='clock16',SAR_SAMPLE_GUARD2='quiet15',SAR_OUTPUT_FF='fast3')
    f='regression/systems/monotonic_sar/flows/physical_clock16_'+group;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

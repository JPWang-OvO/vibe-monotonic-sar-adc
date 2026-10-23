"""Close the measured cold-start, hot settling, and output-transfer limits."""
import copy,re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/logic/SAR_SAMPLE_GUARD2';s=(ROOT/(base+'/quiet/netlist.scs')).read_text().replace('c=5f','c=20f')
write(base+'/quiet20/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['quiet20']={'netlist':'quiet20/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_WAIT_GATE';s=(ROOT/(base+'/damped_hold20/netlist.scs')).read_text()
s=re.sub(r'(Mn_(?:delay|early) .*?)w=20u',r'\1w=22u',s)
write(base+'/damped_hold22/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['damped_hold22']={'netlist':'damped_hold22/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_OUTPUT_FF';s=(ROOT/(base+'/transistor/netlist.scs')).read_text()
for name,width in [('Mn_mb',2),('Mp_mb',4),('Mn_si',2),('Mp_si',4)]:
    s=re.sub(r'('+name+r' .*?)w=\S+',rf'\1w={width}u',s)
write(base+'/fast2/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['fast2']={'netlist':'fast2/netlist.scs'};js(base+'/cell.json',m)
for group in ('slow','corners'):
    source='physical_phase_drive32k' if group=='slow' else 'physical_guard_corners'
    obj=read_json(ROOT/f'regression/systems/monotonic_sar/flows/{source}/flow.json');obj['id']='sar_pvt_closure_'+group
    obj['testbench']='library/testbenches/systems/monotonic_sar/tb_SAR_phase_nodes/spectre/netlist.scs'
    for c in obj['conditions']:c['cell_views'].update(SAR_PHASE='drive32k',SAR_SAMPLE_GUARD2='quiet20',SAR_WAIT_GATE='damped_hold22',SAR_OUTPUT_FF='fast2')
    f='regression/systems/monotonic_sar/flows/physical_pvt_closure_'+group;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

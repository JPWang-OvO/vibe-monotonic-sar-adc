"""Test measured floating-node damping and the remaining bootstrap-off margin."""
import re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/logic/SAR_WAIT_GATE';s=(ROOT/(base+'/damped/netlist.scs')).read_text().replace('c=15f','c=60f')
write(base+'/damped60/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['damped60']={'netlist':'damped60/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_ARM';s=(ROOT/(base+'/transistor/netlist.scs')).read_text().replace('ends SAR_ARM','C_pstack (net92 VDD) capacitor c=5f\nends SAR_ARM')
write(base+'/quiet/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['quiet']={'netlist':'quiet/netlist.scs'};js(base+'/cell.json',m)
for n in (6,8):
    old='library/blocks/logic/SAR_SAMPLE_GUARD10';base=f'library/blocks/logic/SAR_SAMPLE_GUARD{n}'
    s=(ROOT/(old+'/transistor/netlist.scs')).read_text().replace('SAR_SAMPLE_GUARD10',f'SAR_SAMPLE_GUARD{n}')
    s=re.sub(r'I_d'+str(n-1)+r' .*?I_d9 .*?\n',f'I_d{n-1} (N{n-2} Delayed VDD VSS) INVD1BWP7T\n',s,flags=re.S)
    write(base+'/transistor/netlist.scs',s);m=read_json(ROOT/(old+'/cell.json'));m['cell']=f'SAR_SAMPLE_GUARD{n}';js(base+'/cell.json',m)
    base='library/blocks/control/SAR_ASYNC';view=f'weighted4_g{n}'
    s=(ROOT/(base+'/weighted4_fast/netlist.scs')).read_text().replace('SAR_SAMPLE_GUARD10',f'SAR_SAMPLE_GUARD{n}')
    write(base+'/'+view+'/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(base+'/cell.json',m)
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_damped/flow.json');obj['id']=f'sar_physical_refine_g{n}'
    for c in obj['conditions']:c['cell_views'].update(SAR_ASYNC=view,SAR_WAIT_GATE='damped60',SAR_ARM='quiet')
    obj['criteria']['output_hold_errors']={'max':0}
    f=f'regression/systems/monotonic_sar/flows/physical_refine_g{n}';js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

"""Damp the observed final guard-inverter VGD excursion."""
import re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
for n in (2,4):
    old='library/blocks/logic/SAR_SAMPLE_GUARD4';base=f'library/blocks/logic/SAR_SAMPLE_GUARD{n}'
    s=(ROOT/(old+'/transistor/netlist.scs')).read_text().replace('SAR_SAMPLE_GUARD4',f'SAR_SAMPLE_GUARD{n}')
    if n==2:s=re.sub(r'I_d1 .*?I_d3 .*?\n','I_d1 (N0 Delayed VDD VSS) INVD1BWP7T\n',s,flags=re.S)
    s=s.replace(f'ends SAR_SAMPLE_GUARD{n}',f'C_delay (Delayed VSS) capacitor c=5f\nends SAR_SAMPLE_GUARD{n}')
    write(base+'/quiet/netlist.scs',s)
    m=read_json(ROOT/(old+'/cell.json')) if n==2 else read_json(ROOT/(base+'/cell.json'))
    m['cell']=f'SAR_SAMPLE_GUARD{n}';m['views']['quiet']={'netlist':'quiet/netlist.scs'}
    if n==2:m['views']={'quiet':{'netlist':'quiet/netlist.scs'}}
    js(base+'/cell.json',m)
    # Includes resolve through the registered quiet view; preserve an explicit source path.
    async_base='library/blocks/control/SAR_ASYNC';view=f'weighted4_g{n}_quiet'
    s=(ROOT/(async_base+'/weighted4_g4/netlist.scs')).read_text().replace('SAR_SAMPLE_GUARD4',f'SAR_SAMPLE_GUARD{n}')
    if n==2:s=s.replace('SAR_SAMPLE_GUARD2/transistor','SAR_SAMPLE_GUARD2/quiet')
    write(async_base+'/'+view+'/netlist.scs',s);m=read_json(ROOT/(async_base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(async_base+'/cell.json',m)
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_wait_balance20/flow.json');obj['id']=f'sar_guard_g{n}'
    for c in obj['conditions']:c['cell_views'].update(SAR_ASYNC=view,**{f'SAR_SAMPLE_GUARD{n}':'quiet'})
    f=f'regression/systems/monotonic_sar/flows/physical_guard_g{n}';js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

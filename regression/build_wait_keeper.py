"""Keep CompareEnable low while the delayed DAC-settling condition is active."""
import re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/logic/SAR_WAIT_GATE'
original=(ROOT/(base+'/damped240/netlist.scs')).read_text()
for width in (32,64):
    view=f'damped_hold{width}'
    s=re.sub(r'(Mn_(?:delay|early) .*?)w=8u l=0.18u nf=1',rf'\1w={width}u l=0.18u nf={width//8}',original)
    write(base+'/'+view+'/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(base+'/cell.json',m)
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_wait_damped240/flow.json');obj['id']='sar_wait_hold'+str(width)
    for c in obj['conditions']:c['cell_views']['SAR_WAIT_GATE']=view
    f='regression/systems/monotonic_sar/flows/physical_wait_hold'+str(width);js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

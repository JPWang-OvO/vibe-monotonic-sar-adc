"""Reduce clock-driver overlap feedthrough at the required drive current."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/clock/SAR_PHASE'
source=(ROOT/(base+'/clock16/netlist.scs')).read_text()
for view,cap in [('short80',80),('short160',160)]:
    s=source.replace('SAR_DRIVE scale=8\nMn_clock','SAR_DRIVE scale=4\nMn_clock')
    s=s.replace('nch w=8u l=0.72u','nch w=2u l=0.18u').replace('pch w=16u l=0.72u','pch w=4u l=0.18u').replace('c=320f',f'c={cap}f')
    write(base+'/'+view+'/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(base+'/cell.json',m)
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_clock16_slow/flow.json');obj['id']='sar_clock_'+view
    corners=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_clock16_corners/flow.json');obj['conditions'].append(corners['conditions'][1])
    for c in obj['conditions']:c['cell_views']['SAR_PHASE']=view
    f='regression/systems/monotonic_sar/flows/physical_clock_'+view;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

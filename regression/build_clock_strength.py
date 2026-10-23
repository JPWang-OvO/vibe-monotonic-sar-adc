"""Reduce the measured phase-divider Clock node's source impedance."""
import copy
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/clock/SAR_PHASE'
source=(ROOT/(base+'/drive32k/netlist.scs')).read_text()
for view,cap in [('clock8',240),('clock8fast',80)]:
    s=source.replace('I_clk0 (Clks ClksB VDD VSS) INVD1BWP7T','I_clk0 (Clks ClksB VDD VSS) SAR_DRIVE scale=4')
    s=s.replace('nch w=0.5u l=0.72u','nch w=4u l=0.72u').replace('pch w=1u l=0.72u','pch w=8u l=0.72u')
    s=s.replace('C_clock_slew (Clock VSS) capacitor c=20f',f'C_clock_slew (Clock VSS) capacitor c={cap}f')
    write(base+'/'+view+'/netlist.scs',s)
    m=read_json(ROOT/(base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(base+'/cell.json',m)
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_pvt_closure_slow/flow.json');obj['id']='sar_'+view
    for c in obj['conditions']:c['cell_views']['SAR_PHASE']=view
    folder='regression/systems/monotonic_sar/flows/physical_'+view;js(folder+'/flow.json',obj)
    write(folder+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

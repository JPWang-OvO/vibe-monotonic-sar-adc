"""Address full-window SS/hot read timing and measured noisy clock jitter."""
import copy
from regression.common.project import ROOT, read_json
from regression.systems.monotonic_sar.build_behavioral import write, js

base='library/blocks/bias/SAR_BIAS'
s=(ROOT/(base+'/transistor/netlist.scs')).read_text().replace('nch w=1.8u l=2u','nch w=2.7u l=2u')
write(base+'/fast/netlist.scs',s)
m=read_json(ROOT/(base+'/cell.json'));m['views']['fast']={'netlist':'fast/netlist.scs'};js(base+'/cell.json',m)

base='library/blocks/clock/SAR_PHASE'
s=(ROOT/(base+'/short80/netlist.scs')).read_text()
s=s.replace('I_clk0 (Clks ClksB VDD VSS) SAR_DRIVE scale=4','I_clk0 (Clks ClksB VDD VSS) SAR_DRIVE scale=16')
s=s.replace('Mn_clock_slew (Clock ClksB VSS VSS) nch w=2u','Mn_clock_slew (Clock ClksB VSS VSS) nch w=8u')
s=s.replace('Mp_clock_slew (Clock ClksB VDD VDD) pch w=4u','Mp_clock_slew (Clock ClksB VDD VDD) pch w=16u')
s=s.replace('C_clock_slew (Clock VSS) capacitor c=80f','C_clock_slew (Clock VSS) capacitor c=320f')
write(base+'/quiet320/netlist.scs',s)
m=read_json(ROOT/(base+'/cell.json'));m['views']['quiet320']={'netlist':'quiet320/netlist.scs'};js(base+'/cell.json',m)

# The SS/-40 noisy run exposed a 1.982 V excursion at the reset FF's
# floating PMOS stack. The same local damping already closed the ARM cell.
base='library/blocks/logic/SAR_DFFR'
s=(ROOT/(base+'/transistor/netlist.scs')).read_text().replace('ends SAR_DFFR','C_pstack (net92 VDD) capacitor c=5f\nends SAR_DFFR')
write(base+'/quiet/netlist.scs',s)
m=read_json(ROOT/(base+'/cell.json'));m['views']['quiet']={'netlist':'quiet/netlist.scs'};js(base+'/cell.json',m)

for group,source in [('ss','final_stage3_ss_125_k51'),('corners','physical_clock16_corners')]:
    obj=read_json(ROOT/f'regression/systems/monotonic_sar/flows/{source}/flow.json')
    obj['id']='sar_slow_hot_'+group
    if group=='corners':
        baseflow=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_clock_short80/flow.json')
        obj['conditions']=[copy.deepcopy(baseflow['conditions'][0]),copy.deepcopy(obj['conditions'][2])]
    for c in obj['conditions']:
        c['cell_views']=copy.deepcopy(read_json(ROOT/'config/final_design.json')['cell_views'])
        c['cell_views'].update(SAR_BIAS='fast',SAR_PHASE='quiet320')
    folder='regression/systems/monotonic_sar/flows/physical_slow_hot_'+group
    js(folder+'/flow.json',obj)
    write(folder+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
    write(folder+'/measure.py','from regression.systems.monotonic_sar.measure import measure_sar\n')

base=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_slow_hot_ss/flow.json')
obj=copy.deepcopy(base);obj['id']='sar_noise_closure';obj['conditions']=[]
for corner,temp,name in [('ss',125,'ss_125'),('ss',-40,'ss_m40'),('ff',125,'ff_125')]:
    c=copy.deepcopy(base['conditions'][1]);c['id']=name;c['corner']=corner
    c['tokens'].update(TEMP=temp,FIN=3*50e6/256);c['cell_views']['SAR_DFFR']='quiet';obj['conditions'].append(c)
obj['criteria']['sndr_db']['min']=57
obj['simulator']['analyses']='Full 256-code diagnostic of the three demonstrated noisy-corner failures; fixed seed 1'
folder='regression/systems/monotonic_sar/flows/physical_noise_closure';js(folder+'/flow.json',obj)
write(folder+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
write(folder+'/measure.py','from regression.systems.monotonic_sar.measure import measure_sar\n')

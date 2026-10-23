"""Close observed comparator premature completion and divider reset release."""
import copy
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js

def variant(base,view,s):
    write(base+'/'+view+'/netlist.scs',s)
    m=read_json(ROOT/(base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(base+'/cell.json',m)

base='library/blocks/comparator/SAR_CMP'
s=(ROOT/(base+'/current/netlist.scs')).read_text()
for side,node in [('p','Xp'),('n','Xn')]:
    s=s.replace(f'I_out{side} ({node} N{side}0 VDD VSS) INVD1BWP7T',
      f'Mn_sense{side} (N{side}0 {node} VSS VSS) nch w=0.5u l=0.18u nf=1 m=1\n'
      f'Mp_sense{side} (N{side}0 {node} VDD VDD) pch w=4u l=0.18u nf=1 m=1')
variant(base,'sense',s)

base='library/blocks/clock/SAR_PHASE'
s=(ROOT/(base+'/quiet320/netlist.scs')).read_text()
s=s.replace('subckt SAR_PHASE', 'include "../../../logic/SAR_CAPTURE_LATCH/drive/netlist.scs"\ninclude "../../../logic/SAR_SELECT/transistor/netlist.scs"\nsubckt SAR_PHASE')
s=s.replace('I_clk0 (Clks ClksB', 'I_enable (PorN Clks ClockEnable ClockEnableB VDD VSS) SAR_CAPTURE_LATCH\nI_gate (Clks ClockEnable ClockGatedB VDD VSS) SAR_SELECT factor=16\nI_gatebuf (ClockGatedB ClockGated VDD VSS) SAR_DRIVE scale=4\nI_clk0 (ClockGated ClksB')
variant(base,'gated320',s)

base='library/blocks/logic/SAR_DFFS'
s=(ROOT/(base+'/quad/netlist.scs')).read_text().replace('ends SAR_DFFS','C_pstack (net64 VDD) capacitor c=20f\nends SAR_DFFS')
variant(base,'quadquiet',s)

obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_ring_noise/flow.json')
obj['id']='sar_completion_startup';obj['conditions']=[]
source=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_ring_noise/flow.json')['conditions'][0]
for corner,temp,name,k,noise in [('tt',25,'tt_25',3,''),('ss',-40,'ss_m40',3,source['tokens']['NOISE']),('ss',125,'ss_125',51,'')]:
    c=copy.deepcopy(source);c.update(id=name,corner=corner)
    c['tokens'].update(TEMP=temp,FIN=k*50e6/256,NOISE=noise)
    c['cell_views'].update(SAR_CMP='sense',SAR_PHASE='gated320',SAR_DFFS='quadquiet')
    obj['conditions'].append(c)
obj['criteria']['sndr_db']['min']=57
obj['simulator']['analyses']='Full 256-code focused closure: comparator completion sensing and one-hot divider startup'
folder='regression/systems/monotonic_sar/flows/physical_completion_startup'
js(folder+'/flow.json',obj)
write(folder+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
write(folder+'/measure.py','from regression.systems.monotonic_sar.measure import measure_sar\n')

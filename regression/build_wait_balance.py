"""Balance measured settling and output latency, retaining the rated wait gate."""
import re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/clock/SAR_PHASE';s=(ROOT/(base+'/drive8k/netlist.scs')).read_text();s=s[:s.index('I_pre0')]
for i in range(4):s+=f'I_pre{i} (SampleN3 SampleN4 VDD VSS) SAR_DRIVE scale=512\n'
for i in range(32):s+=f'I_final{i} (SampleN4 Sample VDD VSS) SAR_DRIVE scale=512\n'
s+='ends SAR_PHASE\n';write(base+'/drive16k/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['drive16k']={'netlist':'drive16k/netlist.scs'};js(base+'/cell.json',m)
old='library/blocks/logic/SAR_SAMPLE_GUARD6';base='library/blocks/logic/SAR_SAMPLE_GUARD4'
s=(ROOT/(old+'/transistor/netlist.scs')).read_text().replace('SAR_SAMPLE_GUARD6','SAR_SAMPLE_GUARD4')
s=re.sub(r'I_d3 .*?I_d5 .*?\n','I_d3 (N2 Delayed VDD VSS) INVD1BWP7T\n',s,flags=re.S)
write(base+'/transistor/netlist.scs',s);m=read_json(ROOT/(old+'/cell.json'));m['cell']='SAR_SAMPLE_GUARD4';js(base+'/cell.json',m)
base='library/blocks/control/SAR_ASYNC';s=(ROOT/(base+'/weighted4_g6/netlist.scs')).read_text().replace('SAR_SAMPLE_GUARD6','SAR_SAMPLE_GUARD4')
write(base+'/weighted4_g4/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['weighted4_g4']={'netlist':'weighted4_g4/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_WAIT_GATE';original=(ROOT/(base+'/damped240/netlist.scs')).read_text()
for width in (16,20):
    view=f'damped_hold{width}'
    s=re.sub(r'(Mn_(?:delay|early) .*?)w=8u l=0.18u nf=1',rf'\1w={width}u l=0.18u nf=4',original)
    write(base+'/'+view+'/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(base+'/cell.json',m)
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_wait_hold32/flow.json');obj['id']='sar_wait_balance'+str(width)
    for c in obj['conditions']:c['cell_views'].update(SAR_WAIT_GATE=view,SAR_PHASE='drive16k',SAR_ASYNC='weighted4_g4')
    f='regression/systems/monotonic_sar/flows/physical_wait_balance'+str(width);js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

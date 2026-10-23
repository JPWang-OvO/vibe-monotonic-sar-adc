"""Locate sample-period variation and compare a uniformly tapered phase driver."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/clock/SAR_PHASE';s=(ROOT/(base+'/drive16k/netlist.scs')).read_text();s=s[:s.index('I_buffer0')]
for i,scale in enumerate((1,8,64,512)):
    s+=f'I_buffer{i} ({"R0" if i==0 else "SampleN"+str(i-1)} SampleN{i} VDD VSS) SAR_DRIVE scale={scale}\n'
for i in range(8):s+=f'I_pre{i} (SampleN3 SampleN4 VDD VSS) SAR_DRIVE scale=512\n'
for i in range(64):s+=f'I_final{i} (SampleN4 Sample VDD VSS) SAR_DRIVE scale=512\n'
s+='ends SAR_PHASE\n';write(base+'/drive32k/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['drive32k']={'netlist':'drive32k/netlist.scs'};js(base+'/cell.json',m)
tb='library/testbenches/systems/monotonic_sar/tb_SAR_phase_nodes';old='library/testbenches/systems/monotonic_sar/tb_SAR_wait_nodes'
s=(ROOT/(old+'/spectre/netlist.scs')).read_text()+'\nsave '+' '.join('I_adc.I_phase.'+n for n in ['Clock','R0','SampleN0','SampleN1','SampleN2','SampleN3','SampleN4'])+'\n'
write(tb+'/spectre/netlist.scs',s);m=read_json(ROOT/(old+'/cell.json'));m['cell']='tb_SAR_phase_nodes';js(tb+'/cell.json',m)
for view in ('drive16k','drive32k'):
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_guard_g2/flow.json');obj['id']='sar_phase_'+view;obj['testbench']=tb+'/spectre/netlist.scs'
    if view=='drive16k':obj['conditions']=obj['conditions'][:1]
    for c in obj['conditions']:c['cell_views']['SAR_PHASE']=view
    f='regression/systems/monotonic_sar/flows/physical_phase_'+view;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

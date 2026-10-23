"""Reduce measured input-dependent sampling-edge modulation."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/clock/SAR_PHASE'
s=(ROOT/(base+'/drive3/netlist.scs')).read_text();s=s[:s.index('I_buffer0')]
for i,scale in enumerate((1,4,16,64,512)):
    s+=f'I_buffer{i} ({"R0" if i==0 else "SampleN"+str(i-1)} SampleN{i} VDD VSS) SAR_DRIVE scale={scale}\n'
for i in range(8):s+=f'I_final{i} (SampleN4 Sample VDD VSS) SAR_DRIVE scale=512\n'
s+='ends SAR_PHASE\n'
write(base+'/drive4/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['drive4']={'netlist':'drive4/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/blocks/sar_frontend/flows/cap24c28_sine/flow.json');obj['id']='sar_frontend_edge'
for c in obj['conditions']:c['cell_views']['SAR_PHASE']='drive4'
f='regression/blocks/sar_frontend/flows/edge';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

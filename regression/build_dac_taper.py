"""Reduce NAND fanout while preserving the strong final CDAC driver."""
import re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/control/SAR_BIT';s=(ROOT/(base+'/drive/netlist.scs')).read_text()
for side in ('p','n'):
    replacement=''
    for i,scale in enumerate((1,4,32,256)):
        a=f'B{side}Raw' if i==0 else f'B{side}Buf{i-1}';z=f'B{side}' if i==3 else f'B{side}Buf{i}'
        supply='VREFP VREFN' if i==3 else 'VDD VSS';minimum=2 if i==3 else 1
        replacement+=f'I_buf_{side}{i} ({a} {z} {supply}) SAR_DRIVE scale=max({minimum},strength*{scale})\n'
    s,count=re.subn(rf'I_buf_{side}0 .*?\nI_buf_{side}1 .*?\n',replacement,s);assert count==1
write(base+'/taper/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['taper']={'netlist':'taper/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_drive/flow.json');obj['id']='sar_physical_taper'
obj['testbench']='library/testbenches/systems/monotonic_sar/tb_SAR_physical_smoke/spectre/netlist.scs'
for c in obj['conditions']:c['cell_views'].update(SAR_BIT='taper',SAR_ASYNC='startup')
f='regression/systems/monotonic_sar/flows/physical_taper';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

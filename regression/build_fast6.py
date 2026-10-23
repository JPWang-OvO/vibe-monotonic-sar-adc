"""Shorten the measured DAC propagation path while preserving polarity."""
import re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/control/SAR_BIT'
s=(ROOT/(base+'/fast2/netlist.scs')).read_text()
for side in ('p','n'):
    pattern=rf'I_buf_{side}0 .*?\nI_buf_{side}1 .*?\nI_buf_{side}2 .*?\nI_buf_{side}3 .*?\n'
    replacement=f'I_buf_{side}0 (B{side}Raw B{side}Buf VDD VSS) SAR_DRIVE scale=max(1,strength*8)\nI_buf_{side}1 (B{side}Buf B{side} VREFP VREFN) SAR_DRIVE scale=max(1,strength*64)\n'
    s,count=re.subn(pattern,replacement,s)
    assert count==1
write(base+'/fast6/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['fast6']={'netlist':'fast6/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/control_fast5/flow.json');obj['id']='sar_control_fast6'
for c in obj['conditions']:c['cell_views']['SAR_BIT']='fast6'
f='regression/systems/monotonic_sar/flows/control_fast6';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

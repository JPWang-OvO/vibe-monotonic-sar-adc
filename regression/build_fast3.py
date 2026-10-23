"""Drive the measured feedback fanout and isolate comparator regeneration load."""
from regression.build_transistors import save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
save('logic','SAR_HANDSHAKE',['A','Z','VDD','VSS'],
    'I_b0 (A N0 VDD VSS) SAR_DRIVE scale=1\nI_b1 (N0 Z VDD VSS) SAR_DRIVE scale=4\n',
    'include "../../../logic/SAR_DRIVE/transistor/netlist.scs"\n')
def view(base,source):
    write(base+'/fast3/netlist.scs',source);meta=read_json(ROOT/(base+'/cell.json'));meta['views']['fast3']={'netlist':'fast3/netlist.scs'};js(base+'/cell.json',meta)
base='library/blocks/control/SAR_ASYNC';s=(ROOT/(base+'/fast2/netlist.scs')).read_text()
s=s.replace('SAR_DELAY2','SAR_HANDSHAKE');view(base,s)
base='library/blocks/comparator/SAR_CMP';s=(ROOT/(base+'/transistor/netlist.scs')).read_text()
s=s.replace('Mp_bias (BiasDrain Bias VDD VDD) pch w=16u l=0.36u nf=2','Mp_bias (BiasDrain Bias VDD VDD) pch w=24u l=0.36u nf=3')
s=s.replace('Mp_clock (Tail ClkC BiasDrain VDD) pch w=16u l=0.18u nf=4','Mp_clock (Tail ClkC BiasDrain VDD) pch w=24u l=0.18u nf=3')
for side in ('p','n'):
    s=s.replace(f'I_out{side} (X{side} Out{side} VDD VSS) INVD1BWP7T',
        f'I_out{side} (X{side} N{side}0 VDD VSS) INVD1BWP7T\nI_out{side}1 (N{side}0 N{side}1 VDD VSS) SAR_DRIVE scale=1\nI_out{side}2 (N{side}1 Out{side} VDD VSS) SAR_DRIVE scale=4')
s=s.replace('../../../../support/standard_cells/ND2D1BWP7T/spectre/netlist.scs','../../../logic/SAR_NAND2/transistor/netlist.scs').replace('ND2D1BWP7T','SAR_NAND2');view(base,s)
for original,name in [('regression/systems/monotonic_sar/flows/control_fast2/flow.json','regression/systems/monotonic_sar/flows/control_fast3'),('regression/blocks/sar_cmp/flows/extended/flow.json','regression/blocks/sar_cmp/flows/extended3')]:
    obj=read_json(ROOT/original);obj['id']+='3'
    for c in obj['conditions']:
        c['cell_views']['SAR_CMP']='fast3'
        if 'SAR_ASYNC' in c['cell_views']:c['cell_views']['SAR_ASYNC']='fast3'
    js(name+'/flow.json',obj);write(name+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

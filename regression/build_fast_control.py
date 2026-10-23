"""Reduce the measured handshake dead time; retain explicit DAC capture delay."""
from regression.build_transistors import save,std
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
save('logic','SAR_DELAY2',['A','Z','VDD','VSS'],
    'I_d0 (A N0 VDD VSS) INVD1BWP7T\nI_d1 (N0 Z VDD VSS) INVD1BWP7T\n',std('INVD1BWP7T'))
base='library/blocks/control/SAR_ASYNC'
source=(ROOT/(base+'/transistor/netlist.scs')).read_text()
source=source.replace('../../../../support/standard_cells/DFCNQD1BWP7T/spectre/netlist.scs','../../../logic/SAR_DFFR/transistor/netlist.scs').replace('DFCNQD1BWP7T','SAR_DFFR')
source=source.replace('simulator lang=spectre\n','simulator lang=spectre\ninclude "../../../logic/SAR_DELAY2/transistor/netlist.scs"\n',1)
source=source.replace('I_feedback_delay (Valid ValidDelay VDD VSS) SAR_DELAY4','I_feedback_delay (Valid ValidDelay VDD VSS) SAR_DELAY2')
write(base+'/fast/netlist.scs',source);meta=read_json(ROOT/(base+'/cell.json'));meta['views']['fast']={'netlist':'fast/netlist.scs'};js(base+'/cell.json',meta)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/control_smoke/flow.json');obj['id']='sar_control_fast'
conditions=[]
for corner,temp in [('tt',25),('ss',125)]:
    for c in obj['conditions']:
        d=dict(c);d['id']=corner+'_'+c['id'];d['tokens']=dict(c['tokens'],TEMP=temp);d['corner']=corner
        d['cell_views']=dict(c['cell_views'],SAR_PHASE='drive',SAR_ASYNC='fast',SAR_INV='drive');conditions.append(d)
obj['conditions']=conditions
f='regression/systems/monotonic_sar/flows/control_fast';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

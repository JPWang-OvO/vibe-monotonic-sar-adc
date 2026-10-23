"""Local transistor storage cells with explicit clock-feedthrough capacitance.

Native standard-cell instances remain unchanged in their source library.
The local cells preserve the exported transistor network and add a physical
storage-node capacitor to address observed 1.99 V clock-feedthrough excursions.
"""
import re
from regression.common.project import ROOT,read_json
from regression.build_transistors import save
from regression.systems.monotonic_sar.build_behavioral import write,js

for source,name,ports,node in (
    ('DFCNQD1BWP7T','SAR_DFFR',['D','CP','CDN','Q','VDD','VSS'],'net5'),
    ('DFSNQD1BWP7T','SAR_DFFS',['D','CP','SDN','Q','VDD','VSS'],'net13'),
):
    native=(ROOT/f'library/support/standard_cells/{source}/spectre/netlist.scs').read_text()
    body=native.split('\n',3)[3].rsplit('ends ',1)[0]
    body=re.sub(r'// Library name:.*\n|// Cell name:.*\n|// View name:.*\n','',body)
    body=f'// Transistor topology and device parameters derived from {source}.\n'+body
    body+=f'C_storage ({node} VSS) capacitor c=3f\n'
    if name=='SAR_DFFS':body+='C_stack (net60 VDD) capacitor c=3f\n'
    if name=='SAR_DFFR':body+='C_stack (net49 VSS) capacitor c=3f\nC_slave (net100 VSS) capacitor c=3f\n'
    save('logic',name,ports,body)

base='library/blocks/clock/SAR_PHASE'
source=(ROOT/(base+'/transistor/netlist.scs')).read_text()
for old,new in [('DFCNQD1BWP7T','SAR_DFFR'),('DFSNQD1BWP7T','SAR_DFFS')]:
    source=source.replace(f'../../../../support/standard_cells/{old}/spectre/netlist.scs',f'../../../logic/{new}/transistor/netlist.scs').replace(old,new)
write(base+'/storage/netlist.scs',source)
meta=read_json(ROOT/(base+'/cell.json'));meta['views']['storage']={'netlist':'storage/netlist.scs'};js(base+'/cell.json',meta)
obj=read_json(ROOT/'regression/blocks/sar_phase/flows/functional/flow.json');obj['id']='sar_phase_storage'
obj['conditions'][0]['cell_views']['SAR_PHASE']='storage'
f='regression/blocks/sar_phase/flows/storage';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

obj=read_json(ROOT/'regression/blocks/sar_cmp/flows/pvt/flow.json');obj['id']='sar_cmp_bias2'
obj['conditions']=[dict(id='tt',corner='tt',tokens={'TEMP':25},cell_views={'SAR_CMP':'transistor','SAR_BIAS':'transistor'},enrichment=True)]+[c for c in obj['conditions'] if c['corner']=='ss']
f='regression/blocks/sar_cmp/flows/bias2';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

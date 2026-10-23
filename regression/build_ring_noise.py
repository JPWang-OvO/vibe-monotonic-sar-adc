"""Reduce the measured divider FF contribution to sampling-period noise."""
import re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js

for cell,source in [('SAR_DFFR','quiet'),('SAR_DFFS','transistor')]:
    base='library/blocks/logic/'+cell
    s=(ROOT/(base+'/'+source+'/netlist.scs')).read_text()
    s=re.sub(r'\bm=1\b','m=4',s)
    s=re.sub(r'(capacitor c=)(\d+(?:\.\d+)?)f',lambda m:m[1]+format(float(m[2])*4,'g')+'f',s)
    write(base+'/quad/netlist.scs',s)
    m=read_json(ROOT/(base+'/cell.json'));m['views']['quad']={'netlist':'quad/netlist.scs'};js(base+'/cell.json',m)

obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_noise_closure/flow.json')
obj['id']='sar_ring_noise';obj['conditions']=obj['conditions'][:1]
for c in obj['conditions']:c['cell_views'].update(SAR_DFFR='quad',SAR_DFFS='quad')
obj['simulator']['analyses']='SS125 fixed 256-code noisy diagnostic: 4x divider FF multiplicity and proportional internal capacitances'
folder='regression/systems/monotonic_sar/flows/physical_ring_noise';js(folder+'/flow.json',obj)
write(folder+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
write(folder+'/measure.py','from regression.systems.monotonic_sar.measure import measure_sar\n')

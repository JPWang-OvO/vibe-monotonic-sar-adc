"""Strengthen the reference pullup against observed bottom-plate overshoot."""
from regression.build_transistors import save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
save('logic','SAR_DAC_DRIVE',['A','Z','VDD','VSS'],
    'parameters scale=1\nMn (Z A VSS VSS) nch w=2u l=180n nf=1 m=scale\nMp (Z A VDD VDD) pch w=6u l=180n nf=1 m=scale\n')
base='library/blocks/control/SAR_BIT';s=(ROOT/(base+'/strong2/netlist.scs')).read_text()
s=s.replace('subckt SAR_BIT','include "../../../logic/SAR_DAC_DRIVE/transistor/netlist.scs"\nsubckt SAR_BIT')
s=s.replace('VREFP VREFN) SAR_DRIVE','VREFP VREFN) SAR_DAC_DRIVE')
write(base+'/pullup/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['pullup']={'netlist':'pullup/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_weighted4/flow.json');obj['id']='sar_physical_pullup'
for c in obj['conditions']:c['cell_views']['SAR_BIT']='pullup'
f='regression/systems/monotonic_sar/flows/physical_pullup';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

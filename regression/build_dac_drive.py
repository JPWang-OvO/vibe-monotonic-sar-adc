"""Size DAC buffers for the observed 6.144 pF MSB settling load."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/control/SAR_BIT'
s=(ROOT/(base+'/latch/netlist.scs')).read_text().replace('strength*8','strength*16').replace('max(1,strength*64)','max(2,strength*256)')
write(base+'/drive/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['drive']={'netlist':'drive/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_buffered/flow.json');obj['id']='sar_physical_drive'
for c in obj['conditions']:c['cell_views']['SAR_BIT']='drive'
obj['criteria'].update(evaluation_count_errors={'max':0},monotonic_switch_errors={'max':0})
f='regression/systems/monotonic_sar/flows/physical_drive';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

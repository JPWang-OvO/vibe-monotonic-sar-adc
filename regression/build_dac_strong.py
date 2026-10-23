"""Size the selection gate and two inverter stages as one DAC drive path."""
from regression.build_transistors import save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/logic/SAR_NAND2';s=(ROOT/(base+'/transistor/netlist.scs')).read_text()
s=s.replace('subckt SAR_NAND2 (A B Z VDD VSS)','subckt SAR_SELECT (A B Z VDD VSS)\nparameters factor=1').replace('ends SAR_NAND2','ends SAR_SELECT').replace('m=1','m=factor')
write('library/blocks/logic/SAR_SELECT/transistor/netlist.scs',s)
js('library/blocks/logic/SAR_SELECT/cell.json',dict(schema_version=1,cell='SAR_SELECT',ports=['A','B','Z','VDD','VSS'],views={'transistor':{'netlist':'transistor/netlist.scs'}}))
base='library/blocks/control/SAR_BIT';s=(ROOT/(base+'/latch/netlist.scs')).read_text()
s=s.replace('SAR_NAND2/transistor','SAR_SELECT/transistor').replace(') SAR_NAND2',') SAR_SELECT factor=max(1,strength*8)')
s=s.replace('strength*8','strength*32').replace('SAR_SELECT factor=max(1,strength*32)','SAR_SELECT factor=max(1,strength*8)').replace('strength*64','strength*256')
write(base+'/strong2/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['strong2']={'netlist':'strong2/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_CAPTURE_LATCH';s=(ROOT/(base+'/transistor/netlist.scs')).read_text()
for line in s.splitlines():
    if line.startswith(('Mn_q ', 'Mn_qb ')):s=s.replace(line,line.replace('w=1u','w=4u'))
    if line.startswith(('Mp_q ', 'Mp_qb ')):s=s.replace(line,line.replace('w=2u','w=8u'))
write(base+'/drive/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['drive']={'netlist':'drive/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_taper/flow.json');obj['id']='sar_physical_strong'
for c in obj['conditions']:c['cell_views'].update(SAR_BIT='strong2',SAR_CAPTURE_LATCH='drive',SAR_ASYNC='fastseq',SAR_CMP='current')
obj['conditions']=obj['conditions'][1:]
import copy
c=copy.deepcopy(obj['conditions'][0]);c['id']='ss_k51';c['corner']='ss';c['tokens']['TEMP']=125;obj['conditions'].append(c)
obj['measurement']['charge_reference_by_condition']=read_json(ROOT/'config/physical_frontend.json')['charge_reference_by_condition']
tb='library/testbenches/systems/monotonic_sar/tb_SAR_physical_capture'
s=(ROOT/obj['testbench']).read_text()+'\nsave '+' '.join(f'I_adc.Ck{i}' for i in range(10))+'\n'
write(tb+'/spectre/netlist.scs',s);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_physical_capture',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}));obj['testbench']=tb+'/spectre/netlist.scs'
f='regression/systems/monotonic_sar/flows/physical_strong';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

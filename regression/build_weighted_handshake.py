"""Wait longer for the large DAC weights and shorten the final save path."""
import copy
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
body=''
for name in ['Hold','Valid','Done']:
    body+=mos('Mn_'+name,f'Z {name} VSS VSS','nch',4)
body+=mos('Mn_delay','Z Delayed Ndelay VSS','nch',8)+mos('Mn_early','Ndelay Early VSS VSS','nch',8)
body+=mos('Mp_hold','P0 Hold VDD VDD','pch',24)+mos('Mp_done','P1 Done P0 VDD','pch',24)
body+=mos('Mp_delay','P2 Delayed P1 VDD','pch',24)+mos('Mp_early','P2 Early P1 VDD','pch',24)
body+=mos('Mp_valid','Z Valid P2 VDD','pch',24)
save('logic','SAR_WAIT_GATE',['Hold','Valid','Done','Delayed','Early','Z','VDD','VSS'],body)
base='library/blocks/logic/SAR_DONE_DELAY'
s='simulator lang=spectre\ninclude "../../../logic/SAR_DRIVE/transistor/netlist.scs"\nsubckt SAR_DONE_DELAY (A Z VDD VSS)\nI_b0 (A N0 VDD VSS) SAR_DRIVE scale=1\nI_b1 (N0 Z VDD VSS) SAR_DRIVE scale=4\nends SAR_DONE_DELAY\n'
write(base+'/short/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['short']={'netlist':'short/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_STARTUP';s=(ROOT/(base+'/transistor/netlist.scs')).read_text()
s=s.replace('Mp0 (P0 Guard ','Mp0 (P0 NotReady ').replace('Mp1 (HoldN NotReady ','Mp1 (HoldN Guard ')
write(base+'/ordered/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['ordered']={'netlist':'ordered/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/control/SAR_ASYNC'
for early in (4,5):
    s=(ROOT/(base+'/fastseq/netlist.scs')).read_text().replace('SAR_NOR4/transistor','SAR_WAIT_GATE/transistor')
    s=s.replace('I_run_nor (Hold Valid ValidDelay Ck0 CompareEnable VDD VSS) SAR_NOR4',
        f'I_early (Ck{9-early} Early VDD VSS) SAR_DRIVE scale=1\nI_run_nor (Hold Valid Ck0 ValidDelay Early CompareEnable VDD VSS) SAR_WAIT_GATE')
    view=f'weighted{early}';write(base+'/'+view+'/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(base+'/cell.json',m)
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_strong/flow.json');obj['id']='sar_physical_'+view
    for c in obj['conditions']:c['cell_views'].update(SAR_ASYNC=view,SAR_DONE_DELAY='short',SAR_STARTUP='ordered')
    f='regression/systems/monotonic_sar/flows/physical_'+view;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

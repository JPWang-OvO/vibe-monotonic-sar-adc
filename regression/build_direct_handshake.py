"""Release reset after completion falls, using the shorter capture-latch path."""
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
body=''
for i,a in enumerate(('A','B','C')):
    body+=mos('Mn'+str(i),f'Z {a} VSS VSS','nch',4)
    body+=mos('Mp'+str(i),f'{"P"+str(i) if i<2 else "Z"} {a} {"VDD" if i==0 else "P"+str(i-1)} VDD','pch',24)
save('logic','SAR_NOR3_FAST',['A','B','C','Z','VDD','VSS'],body)
base='library/blocks/control/SAR_ASYNC'
for old,new in [('fast7','direct'),('startup','startup_direct')]:
    s=(ROOT/(base+'/'+old+'/netlist.scs')).read_text().replace('SAR_NOR4','SAR_NOR3_FAST')
    s=s.replace('include "../../../logic/SAR_HANDSHAKE/transistor/netlist.scs"\n','').replace('I_feedback_delay (Valid ValidDelay VDD VSS) SAR_HANDSHAKE\n','')
    s=s.replace('Valid ValidDelay Ck0 CompareEnable','Valid Ck0 CompareEnable')
    write(base+'/'+new+'/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views'][new]={'netlist':new+'/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/control_latch/flow.json');obj['id']='sar_control_direct'
for c in obj['conditions']:c['cell_views']['SAR_ASYNC']='direct'
f='regression/systems/monotonic_sar/flows/control_direct';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

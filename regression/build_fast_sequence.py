"""Reduce sequencer clock-to-capture latency with a static TG master/slave FF."""
import copy,re
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js

def inv(name,a,z,n=1,p=2):
    return mos('Mn_'+name,f'{z} {a} VSS VSS','nch',n)+mos('Mp_'+name,f'{z} {a} VDD VDD','pch',p)
def tg(name,a,z,ng,pg,n=2,p=4):
    return mos('Mn_'+name,f'{z} {ng} {a} VSS','nch',n)+mos('Mp_'+name,f'{z} {pg} {a} VDD','pch',p)
def nor(name,a,b,z,n,p):
    return (mos('Mn_'+name+'a',f'{z} {a} VSS VSS','nch',n)+mos('Mn_'+name+'b',f'{z} {b} VSS VSS','nch',n)
            +mos('Mp_'+name+'a',f'P{name} {a} VDD VDD','pch',p)+mos('Mp_'+name+'b',f'{z} {b} P{name} VDD','pch',p))
body=inv('d','D','DB')+tg('mi','DB','M','CPB','CP')
body+=nor('m','M','Reset','MD',1,4)+inv('master_buf','MD','MB',2,4)+tg('mf','MB','M','CP','CPB')
body+=tg('si','MB','S','CP','CPB',4,8)+nor('q','S','Reset','Q',4,12)
body+=inv('sb','Q','SB')+tg('sf','SB','S','CPB','CP')
save('logic','SAR_FAST_SEQ',['D','CP','CPB','Reset','Q','VDD','VSS'],body)
base='library/blocks/control/SAR_ASYNC';s=(ROOT/(base+'/startup/netlist.scs')).read_text()
s=s.replace('include "../../../logic/SAR_DFFR/transistor/netlist.scs"','include "../../../logic/SAR_FAST_SEQ/transistor/netlist.scs"')
s=s.replace('I_seq0','I_cp0 (Valid SeqB VDD VSS) SAR_DRIVE scale=16\nI_cp1 (SeqB Seq VDD VSS) SAR_DRIVE scale=16\nI_reset (ClearN Reset VDD VSS) SAR_DRIVE scale=8\nI_seq0',1)
s=re.sub(r'(I_seq\d+ \([^ ]+) Valid ClearN ([^ ]+) VDD VSS\) SAR_DFFR',r'\1 Seq SeqB Reset \2 VDD VSS) SAR_FAST_SEQ',s)
write(base+'/fastseq/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['fastseq']={'netlist':'fastseq/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/control_latch/flow.json');obj['id']='sar_control_fastseq'
obj['conditions']=[c for c in obj['conditions'] if c['id'].endswith('k51')]
for c in obj['conditions']:c['cell_views'].update(SAR_ASYNC='fastseq',SAR_CMP='fast4')
f='regression/systems/monotonic_sar/flows/control_fastseq';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

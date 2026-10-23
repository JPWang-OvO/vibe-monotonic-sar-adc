"""Reduce the measured 357 ps SS output-register delay with a static TG FF."""
import copy
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
def inv(name,a,z,n,p):return mos('Mn_'+name,f'{z} {a} VSS VSS','nch',n)+mos('Mp_'+name,f'{z} {a} VDD VDD','pch',p)
def tg(name,a,z,ng,pg,n,p):return mos('Mn_'+name,f'{z} {ng} {a} VSS','nch',n)+mos('Mp_'+name,f'{z} {pg} {a} VDD','pch',p)
body=inv('cp','CP','CPB',1,2)+inv('d','D','DB',1,2)
body+=tg('mi','DB','M','CPB','CP',.5,1)+inv('md','M','MD',.5,1)+inv('mb','MD','MB',1,2)+tg('mf','MB','M','CP','CPB',.5,1)
body+=tg('si','MB','S','CP','CPB',1.5,3)+inv('q','S','Q',2,4)+inv('sb','Q','SB',.5,1)+tg('sf','SB','S','CPB','CP',.5,1)
save('logic','SAR_OUTPUT_FF',['D','CP','Q','VDD','VSS'],body)
base='library/blocks/control/SAR_OUT';s=(ROOT/(base+'/transistor/netlist.scs')).read_text()
s=s.replace('include "../../../../support/standard_cells/DFQD1BWP7T/spectre/netlist.scs"','include "../../../logic/SAR_OUTPUT_FF/transistor/netlist.scs"').replace(') DFQD1BWP7T',') SAR_OUTPUT_FF')
write(base+'/fast/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['fast']={'netlist':'fast/netlist.scs'};js(base+'/cell.json',m)
base='library/blocks/logic/SAR_DONE_DELAY';s=(ROOT/(base+'/short/netlist.scs')).read_text().replace('scale=4','scale=16').replace('scale=1\n','scale=4\n')
write(base+'/fastout/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views']['fastout']={'netlist':'fastout/netlist.scs'};js(base+'/cell.json',m)
for mode in ('direct','buffered'):
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_quiet/flow.json');obj['id']='sar_physical_out_'+mode
    for c in obj['conditions']:
        c['cell_views']['SAR_OUT']='fast'
        if mode=='buffered':c['cell_views'].update(MONOTONIC_SAR='spectre',SAR_DONE_DELAY='fastout')
    f='regression/systems/monotonic_sar/flows/physical_out_'+mode;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

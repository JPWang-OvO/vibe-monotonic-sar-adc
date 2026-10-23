"""Lower the observed metastable common mode with stronger regeneration NMOS."""
import copy
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js

base='library/blocks/comparator/SAR_CMP'
for width,nf in [(8,2),(12,3)]:
    s=(ROOT/(base+'/current/netlist.scs')).read_text()
    for side in ['p','n']:
        old=next(line for line in s.splitlines() if line.startswith('Mn_latch_'+side+' '))
        new=old.replace('w=4u','w='+str(width)+'u').replace('nf=1','nf='+str(nf))
        s=s.replace(old,new)
    view='regen'+str(width);write(base+'/'+view+'/netlist.scs',s)
    m=read_json(ROOT/(base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(base+'/cell.json',m)
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_completion_startup/flow.json')
source=obj['conditions'][2];obj['id']='sar_regeneration';obj['conditions']=[]
for name,cmp,bias in [('n8','regen8','fast'),('n12','regen12','fast'),('n12_fast','regen12','fast36')]:
    c=copy.deepcopy(source);c['id']=name;c['cell_views'].update(SAR_CMP=cmp,SAR_BIAS=bias)
    obj['conditions'].append(c)
obj['testbench']=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_clock_short80/flow.json')['testbench']
obj['measurement'].update(n=32,fft=False);obj['criteria'].pop('sndr_db');obj['criteria']['sample_count']={'min':32,'max':32}
obj['simulator']['analyses']='SS125 32-code diagnostic: stronger comparator regeneration with original sensing inverter and handshake'
folder='regression/systems/monotonic_sar/flows/physical_regeneration'
js(folder+'/flow.json',obj)
write(folder+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
write(folder+'/measure.py','from regression.systems.monotonic_sar.measure import measure_sar\n')

candidate=copy.deepcopy(obj);candidate['id']='sar_regen8';candidate['conditions']=[copy.deepcopy(obj['conditions'][0])]
candidate['conditions'][0]['cell_views']['SAR_BIAS']='fast36'
candidate['simulator']['analyses']='SS125 32-code closure: 8 um regeneration NMOS and 3.6 um bias sink'
folder='regression/systems/monotonic_sar/flows/physical_regen8';js(folder+'/flow.json',candidate)
write(folder+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
write(folder+'/measure.py','from regression.systems.monotonic_sar.measure import measure_sar\n')

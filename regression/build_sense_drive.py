"""Recover the measured SS sense delay and bit-5 bottom-plate settling."""
import copy
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js

def variant(base,view,s):
    write(base+'/'+view+'/netlist.scs',s)
    m=read_json(ROOT/(base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(base+'/cell.json',m)

base='library/blocks/comparator/SAR_CMP'
for view,n,p in [('sense2','1','8'),('sense4','2','16')]:
    s=(ROOT/(base+'/sense/netlist.scs')).read_text().replace('nch w=0.5u l=0.18u',f'nch w={n}u l=0.18u').replace('pch w=4u l=0.18u',f'pch w={p}u l=0.18u')
    variant(base,view,s)
base='library/blocks/bias/SAR_BIAS'
for view,width in [('fast36','3.6'),('fast45','4.5')]:
    s=(ROOT/(base+'/fast/netlist.scs')).read_text().replace('nch w=2.7u l=2u',f'nch w={width}u l=2u');variant(base,view,s)
base='library/blocks/control/SAR_ASYNC'
s=(ROOT/(base+'/weighted4_g2_quiet/netlist.scs')).read_text().replace('I_early (Ck5 Early','I_early (Ck4 Early')
variant(base,'weighted5_g2_quiet',s)

base=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_completion_startup/flow.json')
for variant_name,cmp,bias in [('a','sense2','fast36'),('b','sense4','fast36'),('c','sense2','fast45')]:
    for corner in ['tt','ss']:
        obj=copy.deepcopy(base);obj['id']='sar_sense_drive_'+variant_name+'_'+corner
        obj['conditions']=[copy.deepcopy(base['conditions'][0 if corner=='tt' else 2])]
        obj['conditions'][0]['cell_views'].update(SAR_CMP=cmp,SAR_BIAS=bias,SAR_ASYNC='weighted5_g2_quiet')
        if corner=='ss':
            obj['measurement'].update(n=32,fft=False);obj['criteria'].pop('sndr_db');obj['criteria']['sample_count']={'min':32,'max':32}
            obj['testbench']=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_clock_short80/flow.json')['testbench']
        obj['simulator']['analyses']='Sense drive / bias closure '+variant_name+'; TT 256 low-frequency codes or SS125 32-code timing window'
        folder='regression/systems/monotonic_sar/flows/physical_sense_drive_'+variant_name+'_'+corner
        js(folder+'/flow.json',obj)
        write(folder+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
        write(folder+'/measure.py','from regression.systems.monotonic_sar.measure import measure_sar\n')

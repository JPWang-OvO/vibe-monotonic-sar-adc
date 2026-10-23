"""Isolate sampling clock load modulation from switch on-resistance."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
def view(base,name,source):
    write(base+'/'+name+'/netlist.scs',source)
    meta=read_json(ROOT/(base+'/cell.json'));meta['views'][name]={'netlist':name+'/netlist.scs'};js(base+'/cell.json',meta)
base='library/blocks/sampling/SAR_SAMPLE'
source=(ROOT/(base+'/transistor/netlist.scs')).read_text()
source=source.replace('Mn_sample (Top Gate Vin VSS) nch_5 w=1024u l=0.6u nf=128','Mn_sample (Top Gate Vin VSS) nch_5 w=256u l=0.6u nf=32')
view(base,'single256',source)
base='library/blocks/clock/SAR_PHASE'
source=(ROOT/(base+'/storage/netlist.scs')).read_text().replace('SAR_DRIVE scale=1\n','SAR_DRIVE scale=4\n').replace('SAR_DRIVE scale=16\n','SAR_DRIVE scale=64\n')
view(base,'drive',source)
base='library/blocks/logic/SAR_INV'
source=(ROOT/(base+'/transistor/netlist.scs')).read_text().replace('scale=8\n','scale=16\n').replace('scale=64\n','scale=256\n')
view(base,'drive',source)
tb='library/testbenches/blocks/sampling/tb_SAR_SAMPLE_sine'
source=(ROOT/(tb+'/spectre/netlist.scs')).read_text().replace('c=120f','c=30f')
write(tb+'/spectre/netlist.scs',source)
obj=read_json(ROOT/'regression/blocks/sar_sampler/flows/sine/flow.json');obj['id']='sar_sampler_drive'
for c in obj['conditions']:c['cell_views']={'SAR_SAMPLE':'single256','SAR_PHASE':'drive','SAR_INV':'drive'}
f='regression/blocks/sar_sampler/flows/drive';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

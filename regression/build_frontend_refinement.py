"""Apply the junction sensitivity result and size sampling-clock fanout."""
from regression.build_transistors import mos
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
def view(base,name,source):
    write(base+'/'+name+'/netlist.scs',source);meta=read_json(ROOT/(base+'/cell.json'));meta['views'][name]={'netlist':name+'/netlist.scs'};js(base+'/cell.json',meta)
base='library/blocks/sampling/SAR_SAMPLE'
source=(ROOT/(base+'/boost2p/netlist.scs')).read_text().replace('ends SAR_SAMPLE',mos('Mp_junction','Top VDD VDD VDD','pch_5',384,.5)+'ends SAR_SAMPLE')
view(base,'junction384',source)
base='library/blocks/clock/SAR_PHASE';source=(ROOT/(base+'/storage/netlist.scs')).read_text()
source=source.replace('I_buffer0 (R0 SampleB_int VDD VSS) SAR_DRIVE scale=1\nI_buffer1 (SampleB_int Sample VDD VSS) SAR_DRIVE scale=16\n',
    'I_buffer0 (R0 SampleN0 VDD VSS) SAR_DRIVE scale=1\nI_buffer1 (SampleN0 SampleN1 VDD VSS) SAR_DRIVE scale=8\nI_buffer2 (SampleN1 SampleN2 VDD VSS) SAR_DRIVE scale=64\nI_buffer3 (SampleN2 Sample VDD VSS) SAR_DRIVE scale=512\n')
view(base,'drive2',source)
base='library/blocks/logic/SAR_INV';source=(ROOT/(base+'/transistor/netlist.scs')).read_text().replace('scale=1\n','scale=8\n').replace('scale=8\nI_b2','scale=48\nI_b2').replace('scale=64\n','scale=256\n')
view(base,'drive2',source)
obj=read_json(ROOT/'regression/blocks/sar_cdac/flows/junction/flow.json');obj['id']='sar_cdac_junction_opt'
obj['conditions']=[dict(id='p384',corner='tt',tokens={'TEMP':25,'CUNIT':'20f'},cell_views={'SAR_FRONTEND':'parametric','SAR_SAMPLE':'junction384','SAR_CDAC':'scaled'},enrichment=True)]
f='regression/blocks/sar_cdac/flows/junction_opt';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
obj=read_json(ROOT/'regression/blocks/sar_sampler/flows/load_static/flow.json');obj['id']='sar_sampler_junction'
obj['conditions']=[dict(id='c'+str(c),corner='tt',tokens={'TEMP':25,'CLOAD':'10.24p','CCOMP':str(c)+'f'},cell_views={'SAR_SAMPLE':'junction384'},enrichment=True) for c in (30,38)]
f='regression/blocks/sar_sampler/flows/junction';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

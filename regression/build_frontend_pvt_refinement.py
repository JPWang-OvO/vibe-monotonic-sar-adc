"""Balance measured TT/SS junction curvature and sampling edge modulation."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
for base,old,new,replacements in [
    ('library/blocks/sampling/SAR_SAMPLE','junction384','junction408',[('pch_5 w=384u l=0.5u nf=48','pch_5 w=408u l=0.5u nf=51')]),
    ('library/blocks/clock/SAR_PHASE','drive2','drive3',[('scale=64\n','scale=128\n'),('I_buffer3 (SampleN2 Sample VDD VSS) SAR_DRIVE scale=512','I_buffer3 (SampleN2 Sample VDD VSS) SAR_DRIVE scale=512\nI_buffer4 (SampleN2 Sample VDD VSS) SAR_DRIVE scale=512')]),
]:
    source=(ROOT/(base+'/'+old+'/netlist.scs')).read_text()
    for a,b in replacements:source=source.replace(a,b)
    write(base+'/'+new+'/netlist.scs',source);meta=read_json(ROOT/(base+'/cell.json'));meta['views'][new]={'netlist':new+'/netlist.scs'};js(base+'/cell.json',meta)
for mode,path in [('static','regression/blocks/sar_frontend/flows/candidate_static/flow.json'),('sine','regression/blocks/sar_frontend/flows/candidate_sine/flow.json'),('loaded','regression/blocks/sar_cdac/flows/loaded/flow.json')]:
    obj=read_json(ROOT/path);obj['id']='sar_frontend_refined_'+mode
    for c in obj['conditions']:
        c['cell_views']['SAR_SAMPLE']='junction408'
        if 'SAR_PHASE' in c['cell_views']:c['cell_views']['SAR_PHASE']='drive3'
    f='regression/blocks/sar_frontend/flows/refined_'+mode;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

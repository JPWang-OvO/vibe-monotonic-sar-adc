"""Check bootstrap overdrive and CDAC loading as a coupled sampling design."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
for kind,baseflow,source_tb in (
    ('static','regression/blocks/sar_sampler/flows/boost2p/flow.json','library/testbenches/blocks/sampling/tb_SAR_SAMPLE'),
    ('sine','regression/blocks/sar_sampler/flows/sine/flow.json','library/testbenches/blocks/sampling/tb_SAR_SAMPLE_sine'),
):
    tb=source_tb+'_load'
    source=(ROOT/(source_tb+'/spectre/netlist.scs')).read_text().replace('c=10.24p','c=@CLOAD@').replace('c=30f','c=@CCOMP@')
    write(tb+'/spectre/netlist.scs',source);js(tb+'/cell.json',dict(schema_version=1,cell=tb.split('/')[-1],ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
    obj=read_json(ROOT/baseflow);obj['id']='sar_sampler_load_'+kind;obj['testbench']=tb+'/spectre/netlist.scs'
    conditions=[]
    for load in (10.24,40.96):
        for k in ((0,) if kind=='static' else (3,51)):
            tokens={'TEMP':25,'CLOAD':str(load)+'p','CCOMP':'38f'}
            if k:tokens['FIN']=k*50e6/256
            views={'SAR_SAMPLE':'boost2p'}
            if kind=='sine':views.update(SAR_PHASE='drive',SAR_INV='drive')
            conditions.append(dict(id='c'+str(load).replace('.','p')+'_k'+str(k),corner='tt',tokens=tokens,cell_views=views,enrichment=True))
    obj['conditions']=conditions
    f='regression/blocks/sar_sampler/flows/load_'+kind;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

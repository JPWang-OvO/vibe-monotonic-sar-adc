"""Verify the selected compensated front end with the stronger sampling drive."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
flows=[]
for mode,baseflow in [('static','regression/blocks/sar_sampler/flows/load_static/flow.json'),('sine','regression/blocks/sar_sampler/flows/load_sine/flow.json')]:
    obj=read_json(ROOT/baseflow);obj['id']='sar_frontend_candidate_'+mode
    obj['conditions']=[dict(id='c34'+('_k'+str(k) if k else ''),corner='tt',tokens=dict(TEMP=25,CLOAD='10.24p',CCOMP='34f',**({'FIN':k*50e6/256} if k else {})),
        cell_views={'SAR_SAMPLE':'junction384',**({'SAR_PHASE':'drive2','SAR_INV':'drive2'} if k else {})},enrichment=True) for k in ((0,) if mode=='static' else (3,51))]
    if mode=='sine':obj['criteria']['period_error_s']={'max':1e-12}
    flows.append((mode,obj))
obj=read_json(ROOT/'regression/blocks/sar_cdac/flows/junction_opt/flow.json');obj['id']='sar_frontend_candidate_cdac'
tb='library/testbenches/blocks/dac/tb_SAR_CDAC_candidate'
source=(ROOT/obj['testbench']).read_text().replace('ccross=38f','ccross=34f')
write(tb+'/spectre/netlist.scs',source);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_CDAC_candidate',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
obj['testbench']=tb+'/spectre/netlist.scs';flows.append(('cdac',obj))
for mode,obj in flows:
    f='regression/blocks/sar_frontend/flows/candidate_'+mode;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

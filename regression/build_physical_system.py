"""Integrate independently characterized physical blocks without output correction."""
import sys
from pathlib import Path
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
source_batch=Path(sys.argv[1])
result=read_json(source_batch/'cases/sar_frontend_cap24c28_loaded__tt/results.json')
gain=result['charge_gain']
base='library/blocks/frontend/SAR_FRONTEND'
source=(ROOT/(base+'/parametric/netlist.scs')).read_text().replace('ccross=38f unit_cap=20f','ccross=28f unit_cap=24f')
write(base+'/candidate/netlist.scs',source)
meta=read_json(ROOT/(base+'/cell.json'));meta['views']['candidate']={'netlist':'candidate/netlist.scs'};js(base+'/cell.json',meta)
currents=[f'I_adc.I_out{i}.I_buf{j}:3' for i in range(10) for j in (0,1)]
extra=['I_adc.I_frontend.Gp','I_adc.I_frontend.Gn','I_adc.SampleB']+[f'I_adc.B{s}{b}' for s in ('p','n') for b in range(9,0,-1)]+currents
for mode,n,tb_source in [('smoke',32,'tb_SAR_smoke'),('sine',256,'tb_SAR_sine')]:
    tb='library/testbenches/systems/monotonic_sar/tb_SAR_physical_'+mode
    text=(ROOT/('library/testbenches/systems/monotonic_sar/'+tb_source+'/spectre/netlist.scs')).read_text()+'\nsave '+' '.join(extra)+'\n'
    write(tb+'/spectre/netlist.scs',text);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_physical_'+mode,ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/control_fast6/flow.json')
    obj['id']='sar_physical_'+mode;obj['testbench']=tb+'/spectre/netlist.scs';obj['conditions']=obj['conditions'][:2]
    for c in obj['conditions']:
        c['cell_views'].update(SAR_PHASE='drive4',SAR_INV='drive2',SAR_FRONTEND='candidate',SAR_SAMPLE='junction384',SAR_CDAC='scaled',SAR_ASYNC='physical')
    obj['measurement'].update(n=n,fft=(mode=='sine'),physical_frontend=True,charge_gain=gain,charge_gain_source=str(source_batch.name)+'/sar_frontend_cap24c28_loaded__tt',output_buffer_currents=currents)
    obj['criteria'].update(sample_count={'min':n,'max':n},step_diff_error_rms_v={'max':0.003515625*(.10**2+.18**2+.08**2)**.5},wrong_bottom_states={'max':0},output_capture_errors={'max':0},bootstrap_gate_at_first_eval_max_v={'max':.2},sample_window_min_s={'min':3.5e-9},sample_window_max_s={'max':4.5e-9})
    if mode=='sine':obj['criteria']['sndr_db']={'min':57.0}
    obj['simulator'].update(timeout_s=1800,analyses=f'Physical ADC development: {n} consecutive conversions after 16 startup cycles; raw output codes')
    f='regression/systems/monotonic_sar/flows/physical_'+mode;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

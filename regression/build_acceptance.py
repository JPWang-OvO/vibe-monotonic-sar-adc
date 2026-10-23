"""Freeze one candidate's bindings into the required staged 20-case matrix."""
import argparse,copy
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
p=argparse.ArgumentParser();p.add_argument('base_flow');a=p.parse_args()
base=read_json(ROOT/a.base_flow);fixed=read_json(ROOT/'config/acceptance.json')
bindings=base['conditions'][0]['cell_views'];assert all(c['cell_views']==bindings for c in base['conditions'])
tb='library/testbenches/systems/monotonic_sar/tb_SAR_acceptance'
source=(ROOT/base['testbench']).read_text()
import re
source,count=re.subn(r'^tran tran stop=\S+.*$',f'tran tran stop={fixed["transient_stop_s"]:.12g} @NOISE@',source,flags=re.M);assert count==1
write(tb+'/spectre/netlist.scs',source);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_acceptance',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
groups=[('stage1_tt','tt',25,[False]),('stage2_tt','tt',25,[True])]
groups += [('stage3_'+c+('_m40' if temp==-40 else '_125'),c,temp,[False,True]) for c in ('ss','ff') for temp in (-40,125)]
paths=[];case_count=0
for group,corner,temp,noises in groups:
    for k,limit in ((3,57.0),(51,56.5)):
        obj=copy.deepcopy(base);obj['id']=f'sar_{group}_k{k}';obj['testbench']=tb+'/spectre/netlist.scs';obj['conditions']=[]
        for noise in noises:
            spec=f'noisefmin={fixed["noise"]["noisefmin_hz"]:.12g} noisefmax={fixed["noise"]["noisefmax_hz"]:.12g} noiseseed={fixed["noise"]["seed"]}' if noise else ''
            obj['conditions'].append(dict(id='noise' if noise else 'quiet',corner=corner,enrichment=True,cell_views=copy.deepcopy(bindings),tokens=dict(FIN=k*50e6/256,TEMP=temp,NOISE=spec)))
            case_count+=1
        obj['measurement'].update(n=256,fft=True,physical_frontend=True,charge_reference_by_condition=read_json(ROOT/'config/physical_frontend.json')['charge_reference_by_condition'])
        for key in ['discard_cycles','read_offset_s','logic_low_v','logic_high_v']:obj['measurement'][key]=fixed[key]
        obj['criteria'].update(sample_count={'min':256,'max':256},sndr_db={'min':limit},soa_warning_count={'max':0},output_hold_errors={'max':0})
        obj['simulator'].update(timeout_s=3600,analyses=f'Formal {group}, k={k}, fixed 256 consecutive codes; noise bandwidth 1 Hz–50 GHz and seed 1 when enabled')
        folder=f'regression/systems/monotonic_sar/flows/final_{group}_k{k}';js(folder+'/flow.json',obj)
        write(folder+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
        write(folder+'/measure.py','from regression.systems.monotonic_sar.measure import measure_sar\n')
        paths.append(folder+'/flow.json')
assert case_count==20
js('config/final_design.json',dict(source_flow=a.base_flow,cell_views=bindings,acceptance='config/acceptance.json',flows=paths,case_count=20,status='candidate_pending_all_stages'))
print('\n'.join(paths))

"""Run both prescribed 256-code tones on the first aligned physical candidate."""
import copy
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_strong/flow.json')
tb='library/testbenches/systems/monotonic_sar/tb_SAR_physical_capture_sine'
s=(ROOT/obj['testbench']).read_text().replace('stop=1.20u','stop=5.8u')
write(tb+'/spectre/netlist.scs',s);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_physical_capture_sine',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
for k,limit in [(3,57),(51,56.5)]:
    flow=copy.deepcopy(obj);flow['id']=f'sar_strong_sine_k{k}';flow['testbench']=tb+'/spectre/netlist.scs'
    c=flow['conditions'][0];c['id']='tt';c['tokens']['FIN']=k*50e6/256;flow['conditions']=[c]
    flow['measurement'].update(n=256,fft=True);flow['criteria'].update(sample_count={'min':256,'max':256},sndr_db={'min':limit})
    flow['simulator'].update(timeout_s=1800,analyses='Development full physical FFT: fixed 16 startup cycles followed by 256 consecutive raw codes')
    f=f'regression/systems/monotonic_sar/flows/strong_sine_k{k}';js(f+'/flow.json',flow)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

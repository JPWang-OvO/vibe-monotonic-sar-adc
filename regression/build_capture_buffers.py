"""Isolate the sequence flip-flops from the measured capture-latch fanout."""
import re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/control/SAR_ASYNC'
for old in ('direct','startup','startup_direct'):
    s=(ROOT/(base+'/'+old+'/netlist.scs')).read_text();lines=[]
    for line in s.splitlines():
        if line.startswith('I_seq'):line=re.sub(r'\bCk(\d)\b',r'Raw\1',line)
        if line.startswith('ends '):
            for i in range(10):
                lines.extend([f'I_cb{i}a (Raw{i} CkB{i} VDD VSS) SAR_DRIVE scale=1',f'I_cb{i}b (CkB{i} Ck{i} VDD VSS) SAR_DRIVE scale=4'])
        lines.append(line)
    new=old+'_buffered';write(base+'/'+new+'/netlist.scs','\n'.join(lines)+'\n')
    m=read_json(ROOT/(base+'/cell.json'));m['views'][new]={'netlist':new+'/netlist.scs'};js(base+'/cell.json',m)
tb='library/testbenches/systems/monotonic_sar/tb_SAR_physical_buffered'
s=(ROOT/'library/testbenches/systems/monotonic_sar/tb_SAR_physical_smoke/spectre/netlist.scs').read_text()
s+='\nsave '+' '.join([f'I_adc.Ck{i}' for i in range(10)]+[f'I_adc.I_async.Raw{i}' for i in range(10)]+['I_adc.I_cmp.Xp','I_adc.I_cmp.Xn'])+'\n'
write(tb+'/spectre/netlist.scs',s);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_physical_buffered',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
for mode,original,view in [('control_buffered','control_direct','direct_buffered'),('physical_buffered','physical_startup','startup_buffered')]:
    obj=read_json(ROOT/f'regression/systems/monotonic_sar/flows/{original}/flow.json');obj['id']='sar_'+mode
    for c in obj['conditions']:c['cell_views']['SAR_ASYNC']=view
    if mode.startswith('physical'):obj['testbench']=tb+'/spectre/netlist.scs'
    f='regression/systems/monotonic_sar/flows/'+mode;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

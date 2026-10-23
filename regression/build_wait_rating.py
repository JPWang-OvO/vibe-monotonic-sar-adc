"""Resolve measured wait-gate VDS overshoot with capacitance or rated PMOS."""
import copy,re
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
tb='library/testbenches/systems/monotonic_sar/tb_SAR_wait_nodes'
old='library/testbenches/systems/monotonic_sar/tb_SAR_physical_capture'
s=(ROOT/(old+'/spectre/netlist.scs')).read_text()+'\nsave I_adc.I_async.I_run_nor.P2 I_adc.I_async.CompareEnable I_adc.I_async.ValidDelay I_adc.I_async.Early\n'
write(tb+'/spectre/netlist.scs',s);m=read_json(ROOT/(old+'/cell.json'));m['cell']='tb_SAR_wait_nodes';js(tb+'/cell.json',m)
base='library/blocks/logic/SAR_WAIT_GATE';original=(ROOT/(base+'/damped60/netlist.scs')).read_text()
for view in ('damped240','rated96'):
    s=original.replace('c=60f','c=240f') if view=='damped240' else re.sub(r'Mp_valid .*', 'Mp_valid (Z Valid P2 VDD) pch_5 w=96u l=0.5u nf=12 m=1',original).replace('c=60f','c=15f')
    write(base+'/'+view+'/netlist.scs',s);m=read_json(ROOT/(base+'/cell.json'));m['views'][view]={'netlist':view+'/netlist.scs'};js(base+'/cell.json',m)
    obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_refine_g6/flow.json');obj['id']='sar_wait_'+view;obj['testbench']=tb+'/spectre/netlist.scs'
    for c in obj['conditions']:c['cell_views']['SAR_WAIT_GATE']=view
    f='regression/systems/monotonic_sar/flows/physical_wait_'+view;js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

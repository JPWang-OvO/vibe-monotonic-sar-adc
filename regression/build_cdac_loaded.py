"""Measure front-end charge gain with the actual comparator input load."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
obj=read_json(ROOT/'regression/blocks/sar_frontend/flows/candidate_cdac/flow.json');obj['id']='sar_cdac_loaded'
source=(ROOT/obj['testbench']).read_text()
source=source.replace('@MODEL_SETUP@','@MODEL_SETUP@\ninclude "../../../../../blocks/comparator/SAR_CMP/transistor/netlist.scs"\ninclude "../../../../../blocks/bias/SAR_BIAS/transistor/netlist.scs"')
source=source.replace('simulatorOptions options temp=@TEMP@','Vclk (ClkC 0) vsource dc=1.8\nI_bias (Bias VDD 0) SAR_BIAS\nI_cmp (Vp Vn ClkC Outp Outn Valid Bias VDD 0) SAR_CMP\nCLp (Outp 0) capacitor c=50f\nCLn (Outn 0) capacitor c=10f\nCLv (Valid 0) capacitor c=100f\nsimulatorOptions options temp=@TEMP@')
tb='library/testbenches/blocks/dac/tb_SAR_CDAC_loaded'
write(tb+'/spectre/netlist.scs',source);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_CDAC_loaded',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
obj['testbench']=tb+'/spectre/netlist.scs'
obj['conditions']=[dict(id=corner,corner=corner,tokens={'TEMP':temp,'CUNIT':'20f'},cell_views={'SAR_FRONTEND':'parametric','SAR_SAMPLE':'junction384','SAR_CDAC':'scaled','SAR_CMP':'fast3','SAR_BIAS':'transistor'},enrichment=True) for corner,temp in [('tt',25),('ss',125)]]
obj['simulator']['analyses']='Five monotonic charge sequences with actual comparator reset-state input capacitance'
f='regression/blocks/sar_cdac/flows/loaded';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

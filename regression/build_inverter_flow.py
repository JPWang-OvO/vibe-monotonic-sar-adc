from regression.systems.monotonic_sar.build_behavioral import write,js
from regression.common.project import ROOT,read_json

def main():
    base='library/blocks/logic/SAR_INV'
    write(base+'/transistor/netlist.scs','''simulator lang=spectre
// MOS terminal order: D G S B. W is total width, nf is physical fingers.
subckt SAR_INV (A Z VDD VSS)
Mn (Z A VSS VSS) nch w=2u l=180n nf=1 m=1
Mp (Z A VDD VDD) pch w=4u l=180n nf=1 m=1
ends SAR_INV
''')
    rec=read_json(ROOT/(base+'/cell.json'));rec['views']['transistor']={'netlist':'transistor/netlist.scs'};js(base+'/cell.json',rec)
    tb='library/testbenches/blocks/logic/tb_SAR_INV'
    write(tb+'/spectre/netlist.scs','''simulator lang=spectre
@MODEL_SETUP@
include "../../../../../blocks/logic/SAR_INV/transistor/netlist.scs"
VDD_SRC (VDD 0) vsource dc=1.8
VIN (IN 0) vsource dc=0 type=pulse val0=0 val1=1.8 delay=1n rise=20p fall=20p width=.98n period=2n
XINV (IN OUT VDD 0) SAR_INV
CL (OUT 0) capacitor c=10f
simulatorOptions options temp=@TEMP@
dc dc dev=VIN param=dc start=0 stop=1.8 step=0.1
tran tran stop=6n
saveOptions options save=selected
save IN OUT VDD_SRC:p
''')
    js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_INV',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
    flow=dict(schema_version=1,id='sar_inv',testbench=tb+'/spectre/netlist.scs',process='tsmc18',
        conditions=[dict(id=c,corner=c,tokens={'TEMP':temp},cell_views={'SAR_INV':'transistor'},enrichment=True) for c,temp in [('tt',25),('ss',125),('ff',-40)]],
        simulator=dict(arguments=['-64','+preset=ax'],threads=8,timeout_s=120,analyses='DC and 6 ns inverter transient',precision={'preset':'AX'}),
        measurement=dict(kind='inverter',samples=[dict(time_s=(i+.5)*1e-9,expected=1-i%2) for i in range(6)]),
        criteria={'vol_max_v':{'max':.18},'voh_min_v':{'min':1.62},'dc_low_input_output_v':{'min':1.62},'dc_high_input_output_v':{'max':.18}})
    f='regression/blocks/sar_inv/flows/functional';js(f+'/flow.json',flow)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
    write(f+'/measure.py','from regression.common.measure import measure\n')

if __name__=='__main__':main()

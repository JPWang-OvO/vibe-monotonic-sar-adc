from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js

tb='library/testbenches/blocks/sampling/tb_SAR_SAMPLE_sine'
source='''simulator lang=spectre
@MODEL_SETUP@
include "../../../../../blocks/sampling/SAR_SAMPLE/transistor/netlist.scs"
include "../../../../../blocks/clock/SAR_PHASE/transistor/netlist.scs"
include "../../../../../blocks/logic/SAR_INV/transistor/netlist.scs"
VDD_SRC (VDD 0) vsource type=pwl wave=[0 0 10n 1.8]
Vref (Ref 0) vsource dc=1.8
VinP (Vinp 0) vsource type=sine dc=0.9 ampl=0.802125844320371 freq=@FIN@
VinN (Vinn 0) vsource type=sine dc=0.9 ampl=-0.802125844320371 freq=@FIN@
Vclock (Clks 0) vsource type=pulse val0=0 val1=1.8 delay=20n rise=20p fall=20p width=1.98n period=4n
I_phase (Clks Sample VDD 0) SAR_PHASE
I_inv (Sample SampleB VDD 0) SAR_INV
I_sp (Vinp Vp Sample SampleB Gp VDD 0) SAR_SAMPLE
I_sn (Vinn Vn Sample SampleB Gn VDD 0) SAR_SAMPLE
Ccomp_p (Gp Vn) capacitor c=120f
Ccomp_n (Gn Vp) capacitor c=120f
Cp (Vp Ref) capacitor c=10.24p
Cn (Vn Ref) capacitor c=10.24p
simulatorOptions options temp=@TEMP@
tran tran stop=5.80u
saveOptions options save=selected
save Sample SampleB Clks Vinp Vinn Vp Vn Gp Gn VDD_SRC:p
'''
write(tb+'/spectre/netlist.scs',source);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_SAMPLE_sine',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
f='regression/blocks/sar_sampler/flows/sine'
obj=dict(schema_version=1,id='sar_sampler_sine',testbench=tb+'/spectre/netlist.scs',process='tsmc18',
 conditions=[dict(id='k'+str(k),corner='tt',tokens={'TEMP':25,'FIN':k*50e6/256},cell_views={},enrichment=True) for k in (3,51)],
 simulator=dict(arguments=['-64','+preset=ax'],threads=8,timeout_s=600,analyses='Sampler held-voltage FFT: 256 consecutive samples after 16 startup cycles, fixed 1 ns hold read',precision={'preset':'AX'}),
 measurement=dict(kind='sar_sampler_sine',n=256,discard_cycles=16,read_offset_s=1e-9),
 criteria=dict(sample_count={'min':256,'max':256},sndr_db={'min':70.17},hold_feedthrough_max_v={'max':.00028125},period_error_s={'max':50e-12}))
js(f+'/flow.json',obj);write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

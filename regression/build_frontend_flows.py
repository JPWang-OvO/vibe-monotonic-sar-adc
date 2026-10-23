from regression.systems.monotonic_sar.build_behavioral import write,js

def flow(name,tb,measurement,criteria,conditions=None):
    f='regression/blocks/'+name+'/flows/functional'
    obj=dict(schema_version=1,id=name,testbench=tb+'/spectre/netlist.scs',process='tsmc18',
        conditions=conditions or [dict(id='tt',corner='tt',tokens={'TEMP':25},cell_views={},enrichment=True)],
        simulator=dict(arguments=['-64','+preset=ax'],threads=8,timeout_s=300,analyses=name+' transistor module functional transient',precision={'preset':'AX'}),
        measurement=measurement,criteria=criteria)
    js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

def main():
    tb='library/testbenches/blocks/clock/tb_SAR_PHASE'
    source='''simulator lang=spectre
@MODEL_SETUP@
include "../../../../../blocks/clock/SAR_PHASE/transistor/netlist.scs"
VDD_SRC (VDD 0) vsource type=pwl wave=[0 0 10n 1.8]
Vclock (Clks 0) vsource type=pulse val0=0 val1=1.8 delay=20n rise=20p fall=20p width=1.98n period=4n
I_phase (Clks Sample VDD 0) SAR_PHASE
Cload (Sample 0) capacitor c=500f
simulatorOptions options temp=@TEMP@
tran tran stop=600n
saveOptions options save=selected
save Sample Clks I_phase.PorRamp I_phase.PorN I_phase.R0 I_phase.R1 I_phase.R2 I_phase.R3 I_phase.R4 VDD_SRC:p
'''
    write(tb+'/spectre/netlist.scs',source);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_PHASE',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
    flow('sar_phase',tb,dict(kind='sar_phase'),dict(pulse_count={'min':18,'max':20},period_error_s={'max':50e-12},width_min_s={'min':3.5e-9},width_max_s={'max':4.5e-9}))
    tb='library/testbenches/blocks/sampling/tb_SAR_SAMPLE';points=[.1,.5,.9,1.3,1.7]
    source='''simulator lang=spectre
@MODEL_SETUP@
include "../../../../../blocks/sampling/SAR_SAMPLE/transistor/netlist.scs"
VDD_SRC (VDD 0) vsource type=pwl wave=[0 0 10n 1.8]
Vs (Sample 0) vsource type=pulse val0=0 val1=1.8 delay=20n rise=20p fall=20p width=3.98n period=20n
Vsb (SampleB 0) vsource type=pulse val0=1.8 val1=0 delay=20n rise=20p fall=20p width=3.98n period=20n
'''
    for side,sign in [('p',1),('n',-1)]:
        values=[0,.9+sign*(points[0]-.9)];previous=values[1]
        for j,p in enumerate(points):
            v=.9+sign*(p-.9);tm=50e-9+j*40e-9
            values.extend([tm,previous,tm+20e-12,v]);previous=v
        source+=f'Vin{side} (Vin{side} 0) vsource type=pwl wave=['+' '.join(f'{v:.14g}' for v in values)+']\n'
    source+='''I_sp (Vinp Vp Sample SampleB VDD 0) SAR_SAMPLE
I_sn (Vinn Vn Sample SampleB VDD 0) SAR_SAMPLE
Cp (Vp VDD) capacitor c=10.24p
Cn (Vn VDD) capacitor c=10.24p
simulatorOptions options temp=@TEMP@
tran tran stop=242n
saveOptions options save=selected
save Sample SampleB Vinp Vinn Vp Vn I_sp.Gate I_sp.Ct I_sp.Cb I_sp.Q I_sp.ResetMid I_sn.Gate I_sn.Ct I_sn.Cb I_sn.Q I_sn.ResetMid VDD_SRC:p
'''
    write(tb+'/spectre/netlist.scs',source);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_SAMPLE',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
    flow('sar_sampler',tb,dict(kind='sar_sampler',points=points),dict(sample_error_max_v={'max':.0003515625},hold_drift_max_v={'max':.00017578125},bootstrap_min_v={'min':1.6},bootstrap_max_v={'max':1.9}))

if __name__=='__main__':main()

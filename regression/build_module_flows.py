from regression.systems.monotonic_sar.build_behavioral import write,js
from regression.common.project import ROOT,read_json

def main():
    # Timed VA uses the allocated per-bit analog/settling budget.
    for category,name,param,value in [('comparator','SAR_CMP','tcompare','600p'),('control','SAR_ASYNC','tsettle','600p')]:
        base=f'library/blocks/{category}/{name}'
        rec=read_json(ROOT/(base+'/cell.json'));ports=rec['ports']
        source=f'ahdl_include "../veriloga/{name}.va"\nsubckt {name} ('+' '.join(ports)+')\nI_model ('+' '.join(ports)+f') {name}_va {param}={value}\nends {name}\n'
        write(base+'/timed/netlist.scs',source);rec['views']['timed']={'netlist':'timed/netlist.scs'};js(base+'/cell.json',rec)
    flow=read_json(ROOT/'regression/systems/monotonic_sar/flows/behavioral/flow.json');flow['id']='sar_timed'
    for c in flow['conditions']:c['cell_views'].update(SAR_CMP='timed',SAR_ASYNC='timed')
    f='regression/systems/monotonic_sar/flows/timed'
    js(f+'/flow.json',flow);write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n');write(f+'/measure.py','from regression.systems.monotonic_sar.measure import measure_sar\n')
    points=[]
    for cm in (.9,.45,.1125,.0140625,.0017578125):
        for dv in (.00087890625,-.00087890625,.003515625,-.003515625):
            points.append(dict(common_mode_v=cm,differential_v=dv))
    tb='library/testbenches/blocks/comparator/tb_SAR_CMP'
    source='''simulator lang=spectre
@MODEL_SETUP@
include "../../../../../blocks/comparator/SAR_CMP/transistor/netlist.scs"
include "../../../../../blocks/bias/SAR_BIAS/transistor/netlist.scs"
VDD_SRC (VDD 0) vsource type=pwl wave=[0 0 10n 1.8]
Vclock (ClkC 0) vsource type=pulse val0=1.8 val1=0 delay=52n rise=20p fall=20p width=3.98n period=10n
'''
    for side,sign in [('p',1),('n',-1)]:
        values=[0,points[0]['common_mode_v']+sign*points[0]['differential_v']/2]
        previous=values[1]
        for j,p in enumerate(points):
            value=p['common_mode_v']+sign*p['differential_v']/2
            time=50e-9+j*10e-9
            values.extend([time,previous,time+20e-12,value]);previous=value
        source+=f'Vin{side} (V{side} 0) vsource type=pwl wave=['+' '.join(f'{v:.14g}' for v in values)+']\n'
    source+='''I_bias (Bias VDD 0) SAR_BIAS
I_cmp (Vp Vn ClkC Outp Outn Valid Bias VDD 0) SAR_CMP
CLp (Outp 0) capacitor c=20f
CLn (Outn 0) capacitor c=20f
CLv (Valid 0) capacitor c=50f
simulatorOptions options temp=@TEMP@
tran tran stop=252n
saveOptions options save=selected
save Vp Vn ClkC Outp Outn Valid Bias I_cmp.Xp I_cmp.Xn I_cmp.Tail I_cmp.BiasDrain VDD_SRC:p
'''
    write(tb+'/spectre/netlist.scs',source);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_CMP',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
    flow=dict(schema_version=1,id='sar_cmp',testbench=tb+'/spectre/netlist.scs',process='tsmc18',
        conditions=[dict(id='tt',corner='tt',tokens={'TEMP':25},cell_views={'SAR_CMP':'transistor','SAR_BIAS':'transistor'},enrichment=True)],
        simulator=dict(arguments=['-64','+preset=ax'],threads=8,timeout_s=300,analyses='20 comparisons at five common modes and both polarities; transistor bias startup',precision={'preset':'AX'}),
        measurement=dict(kind='sar_comparator',points=points,start_s=52.01e-9,period_s=10e-9),
        criteria={'wrong_decisions':{'max':0},'missing_valid':{'max':0},'reset_errors':{'max':0},'delay_max_s':{'max':1.3e-9},'bias_min_v':{'min':.75},'bias_max_v':{'max':1.4}})
    f='regression/blocks/sar_cmp/flows/functional';js(f+'/flow.json',flow)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n');write(f+'/measure.py','from regression.systems.monotonic_sar.measure_modules import measure_comparator\n')

if __name__=='__main__':main()

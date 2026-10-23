"""Charge redistribution with the real disabled sampling MOS and fixed inputs."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
from regression.systems.monotonic_sar.model import convert
base='library/blocks/dac/SAR_CDAC'
ports=read_json(ROOT/(base+'/cell.json'))['ports']
source='subckt SAR_CDAC ('+' '.join(ports)+')\nparameters unit_cap=20f\n'
for side in ('p','n'):
    for bit in range(9,0,-1):source+=f'C{side}{bit} (V{side} B{side}{bit}) capacitor c={2**(bit-1)}*unit_cap\n'
    source+=f'C{side}_dummy (V{side} VREFP) capacitor c=unit_cap\n'
source+='ends SAR_CDAC\n';write(base+'/scaled/netlist.scs',source)
meta=read_json(ROOT/(base+'/cell.json'));meta['views']['scaled']={'netlist':'scaled/netlist.scs'};js(base+'/cell.json',meta)
base='library/blocks/frontend/SAR_FRONTEND'
source=(ROOT/(base+'/transistor/netlist.scs')).read_text().replace('parameters ccross=120f','parameters ccross=38f unit_cap=20f').replace(') SAR_CDAC',') SAR_CDAC unit_cap=unit_cap')
write(base+'/parametric/netlist.scs',source);meta=read_json(ROOT/(base+'/cell.json'));meta['views']['parametric']={'netlist':'parametric/netlist.scs'};js(base+'/cell.json',meta)
tb='library/testbenches/blocks/dac/tb_SAR_CDAC_physical'
source='''simulator lang=spectre
@MODEL_SETUP@
include "../../../../../blocks/frontend/SAR_FRONTEND/transistor/netlist.scs"
VDD_SRC (VDD 0) vsource type=pwl wave=[0 0 10n 1.8]
Vref (Ref 0) vsource dc=1.8
Vs (Sample 0) vsource type=pulse val0=0 val1=1.8 delay=20n rise=20p fall=20p width=3.98n period=40n
Vsb (SampleB 0) vsource type=pulse val0=1.8 val1=0 delay=20n rise=20p fall=20p width=3.98n period=40n
'''
points=[.1,.5,.9,1.3,1.7];sequences=[]
for v in points:sequences.append(convert(v,1.8-v)[1])
for side in ('p','n'):
    values=[0,points[0] if side=='p' else 1.8-points[0]];prev=values[1]
    for j,v in enumerate(points):
        value=v if side=='p' else 1.8-v;at=18e-9+j*40e-9
        values.extend([at,prev,at+20e-12,value]);prev=value
    source+=f'Vin{side} (Vin{side} 0) vsource type=pwl wave=['+' '.join(f'{v:.14g}' for v in values)+']\n'
    for bit in range(9,0,-1):
        values=[0,1.8];prev=1.8
        for j,trace in enumerate(sequences):
            start=20e-9+j*40e-9
            values.extend([start,prev,start+20e-12,1.8]);prev=1.8
            step=next(s for s in trace if s['bit']==bit)
            value=0 if step['switched_side']==side else 1.8
            at=start+5e-9+(9-bit)*1e-9
            values.extend([at,prev,at+20e-12,value]);prev=value
        source+=f'Vb{side}{bit} (B{side}{bit} 0) vsource type=pwl wave=['+' '.join(f'{v:.14g}' for v in values)+']\n'
ports=read_json(ROOT/'library/blocks/frontend/SAR_FRONTEND/cell.json')['ports']
nodes=[{'VREFP':'Ref','VREFN':'0','VSS':'0'}.get(p,p) for p in ports]
source+='I_front ('+' '.join(nodes)+') SAR_FRONTEND unit_cap=@CUNIT@ ccross=38f\n'
source+='simulatorOptions options temp=@TEMP@\ntran tran stop=199n\nsaveOptions options save=selected\nsave Sample SampleB Vinp Vinn Vp Vn I_front.Gp I_front.Gn VDD_SRC:p\n'
write(tb+'/spectre/netlist.scs',source);js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_CDAC_physical',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
flow=dict(schema_version=1,id='sar_cdac_physical',testbench=tb+'/spectre/netlist.scs',process='tsmc18',
    conditions=[dict(id='unit'+str(c),corner='tt',tokens={'TEMP':25,'CUNIT':str(c)+'f'},cell_views={'SAR_FRONTEND':'parametric','SAR_SAMPLE':'boost2p','SAR_CDAC':'scaled'},enrichment=True) for c in (20,80)],
    simulator=dict(arguments=['-64','+preset=ax'],threads=8,timeout_s=300,analyses='Physical sampler/CDAC charge redistribution: five fixed inputs, nine monotonic bottom steps; independent module diagnostic',precision={'preset':'AX'}),
    measurement=dict(kind='sar_cdac',points=points,sequences=sequences),criteria=dict(settling_error_max_v={'max':.0003515625},nonlinear_residual_rms_v={'max':.0003515625}))
f='regression/blocks/sar_cdac/flows/physical';js(f+'/flow.json',flow)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

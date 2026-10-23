"""Generate the ADC-specific module set and two-frequency behavioral flow."""
import json
from pathlib import Path
from .model import ROOT,PARAMS

def write(path,text):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text,encoding='utf-8',newline='\n')

def js(path,obj):write(path,json.dumps(obj,indent=2)+'\n')

def cell(category,name,ports,body,view='veriloga'):
    base=f'library/blocks/{category}/{name}'
    if view=='veriloga':
        va='`include "constants.vams"\n`include "disciplines.vams"\n'+body
        write(f'{base}/veriloga/{name}.va',va)
        net=f'ahdl_include "{name}.va"\nsubckt {name} ('+ ' '.join(ports)+f')\nI_model ('+' '.join(ports)+f') {name}_va\nends {name}\n'
        write(f'{base}/veriloga/netlist.scs',net)
        views={'veriloga':{'source':f'veriloga/{name}.va','netlist':'veriloga/netlist.scs'}}
    else:
        write(f'{base}/{view}/netlist.scs',body)
        views={view:{'netlist':f'{view}/netlist.scs'}}
    js(f'{base}/cell.json',dict(schema_version=1,cell=name,ports=ports,views=views))

def main():
    cell('clock','SAR_PHASE',['Clks','Sample','VDD','VSS'],'''module SAR_PHASE_va(Clks,Sample,VDD,VSS);
input Clks,VDD,VSS; output Sample; electrical Clks,Sample,VDD,VSS;
integer count,s;
analog begin
 @(initial_step) begin count=4;s=0;end
 @(cross(V(Clks,VSS)-0.9,+1)) begin count=(count+1)%5;s=(count==0);end
 V(Sample,VSS)<+transition(s*1.8,0,1p,1p);
end
endmodule
''')
    cell('sampling','SAR_SAMPLE',['Vin','Top','Sample','SampleB','Gate','VDD','VSS'],'''module SAR_SAMPLE_va(Vin,Top,Sample,SampleB,Gate,VDD,VSS);
inout Vin,Top; input Sample,SampleB,VDD,VSS; output Gate;
electrical Vin,Top,Sample,SampleB,Gate,VDD,VSS;
integer on;
analog begin
 @(initial_step) on=0;
 @(cross(V(Sample,VSS)-0.9,+1)) on=1;
 @(cross(V(Sample,VSS)-0.9,-1)) on=0;
 V(Gate,VSS)<+transition(on,0,20p,20p)*(V(Vin,VSS)+V(VDD,VSS));
 if(on) V(Vin,Top)<+0;
 else I(Vin,Top)<+0;
end
endmodule
''')
    cell('logic','SAR_INV',['A','Z','VDD','VSS'],'''module SAR_INV_va(A,Z,VDD,VSS);
input A,VDD,VSS;output Z;electrical A,Z,VDD,VSS;
integer q;
analog begin
 @(initial_step) q=1;
 @(cross(V(A,VSS)-0.9,0)) q=(V(A,VSS)<0.9);
 V(Z,VSS)<+transition(q*1.8,0,1p,1p);
end
endmodule
''')
    cell('comparator','SAR_CMP',['Vp','Vn','ClkC','Outp','Outn','Valid','Bias','VDD','VSS'],'''module SAR_CMP_va(Vp,Vn,ClkC,Outp,Outn,Valid,Bias,VDD,VSS);
input Vp,Vn,ClkC,Bias,VDD,VSS;output Outp,Outn,Valid;
electrical Vp,Vn,ClkC,Outp,Outn,Valid,Bias,VDD,VSS;
parameter real tcompare=200p;
integer p,n,v,pending;
real completion;
analog begin
 @(initial_step) begin p=1;n=1;v=0;pending=0;completion=1e9;end
 @(cross(V(ClkC,VSS)-0.9,+1)) begin p=1;n=1;v=0;pending=0;end
 @(cross(V(ClkC,VSS)-0.9,-1)) begin pending=1;completion=$abstime+tcompare;end
 @(timer(completion)) begin
   if(pending && V(ClkC,VSS)<0.9) begin
     p=(V(Vp,Vn)>=0);n=1-p;v=1;pending=0;
   end
 end
 V(Outp,VSS)<+transition(p*1.8,0,1p,1p);
 V(Outn,VSS)<+transition(n*1.8,0,1p,1p);
 V(Valid,VSS)<+transition(v*1.8,0,1p,1p);
end
endmodule
''')
    # Every next evaluation is scheduled only after a completion handshake.
    ck=[f'Ck{i}' for i in range(9,-1,-1)]
    body='module SAR_ASYNC_va('+','.join(['Sample','Valid','ClkC','Done']+ck+['VDD','VSS'])+');\n'
    body+='input Sample,Valid,VDD,VSS;output ClkC,Done,'+','.join(ck)+';\n'
    body+='electrical '+','.join(['Sample','Valid','ClkC','Done']+ck+['VDD','VSS'])+';\n'
    body+='parameter real tsettle=300p;\ninteger clock_reset,done,bit_index,running;\ninteger ck[0:9];\ninteger i;real next_eval;\nanalog begin\n'
    body+=' @(initial_step) begin clock_reset=1;done=0;bit_index=9;running=0;next_eval=1e9;for(i=0;i<10;i=i+1)ck[i]=0;end\n'
    body+=' @(cross(V(Sample,VSS)-0.9,+1)) begin clock_reset=1;done=0;running=0;bit_index=9;for(i=0;i<10;i=i+1)ck[i]=0;end\n'
    body+=' @(cross(V(Sample,VSS)-0.9,-1)) begin running=1;next_eval=$abstime+tsettle;end\n'
    body+=' @(timer(next_eval)) begin if(running && !done)clock_reset=0;end\n'
    body+=' @(cross(V(Valid,VSS)-0.9,+1)) begin\n  if(running && !clock_reset && !done) begin\n   ck[bit_index]=1;clock_reset=1;\n   if(bit_index==0)begin done=1;running=0;end\n   else begin bit_index=bit_index-1;next_eval=$abstime+tsettle;end\n  end\n end\n'
    body+=' V(ClkC,VSS)<+transition(clock_reset*1.8,20p,1p,1p);\n V(Done,VSS)<+transition(done*1.8,60p,1p,1p);\n'
    for i in range(10):body+=f' V(Ck{i},VSS)<+transition(ck[{i}]*1.8,0,1p,1p);\n'
    body+='end\nendmodule\n'
    cell('control','SAR_ASYNC',['Sample','Valid','ClkC','Done']+ck+['VDD','VSS'],body)
    cell('control','SAR_BIT',['Outp','Capture','Sample','Q','Bp','Bn','VDD','VSS'],'''module SAR_BIT_va(Outp,Capture,Sample,Q,Bp,Bn,VDD,VSS);
input Outp,Capture,Sample,VDD,VSS;output Q,Bp,Bn;
electrical Outp,Capture,Sample,Q,Bp,Bn,VDD,VSS;
integer q,enabled;
analog begin
 @(initial_step) begin q=0;enabled=0;end
 @(cross(V(Sample,VSS)-0.9,+1)) enabled=0;
 @(cross(V(Capture,VSS)-0.9,+1)) begin q=(V(Outp,VSS)>=0.9);enabled=1;end
 V(Q,VSS)<+transition(q*1.8,0,1p,1p);
 V(Bp,VSS)<+transition((1-enabled*q)*1.8,20p,1p,1p);
 V(Bn,VSS)<+transition((1-enabled*(1-q))*1.8,20p,1p,1p);
end
endmodule
''')
    cell('control','SAR_OUT',['D','Done','Q','VDD','VSS'],'''module SAR_OUT_va(D,Done,Q,VDD,VSS);
input D,Done,VDD,VSS;output Q;electrical D,Done,Q,VDD,VSS;integer q;
analog begin
 @(initial_step)q=0;
 @(cross(V(Done,VSS)-0.9,+1))q=(V(D,VSS)>=0.9);
 V(Q,VSS)<+transition(q*1.8,0,1p,1p);
end
endmodule
''')
    cell('bias','SAR_BIAS',['Bias','VDD','VSS'],'''module SAR_BIAS_va(Bias,VDD,VSS);
input VDD,VSS;output Bias;electrical Bias,VDD,VSS;
analog V(Bias,VSS)<+0.9;
endmodule
''')
    bp=[f'Bp{i}' for i in range(9,0,-1)];bn=[f'Bn{i}' for i in range(9,0,-1)]
    ports=['Vp','Vn']+bp+bn+['VREFP','VREFN']
    cap='subckt SAR_CDAC ('+' '.join(ports)+')\n'
    for i,w in zip(range(9,0,-1),PARAMS['weights']):
        cap+=f'Cp{i} (Vp Bp{i}) capacitor c={w*PARAMS["unit_cap_f"]:.12g}\nCn{i} (Vn Bn{i}) capacitor c={w*PARAMS["unit_cap_f"]:.12g}\n'
    cap+=f'Cp_dummy (Vp VREFP) capacitor c={PARAMS["unit_cap_f"]}\nCn_dummy (Vn VREFP) capacitor c={PARAMS["unit_cap_f"]}\nends SAR_CDAC\n'
    cell('dac','SAR_CDAC',ports,cap,'spectre')
    base='library/systems/monotonic_sar/MONOTONIC_SAR'
    ports=['Vinp','Vinn','Clks']+[f'D{i}' for i in range(9,-1,-1)]+['EOC','VDD','VSS','VCM','VREFP','VREFN']
    modules={'SAR_PHASE':'clock','SAR_SAMPLE':'sampling','SAR_INV':'logic','SAR_CMP':'comparator','SAR_ASYNC':'control','SAR_BIT':'control','SAR_OUT':'control','SAR_BIAS':'bias','SAR_CDAC':'dac'}
    top='simulator lang=spectre\n'
    for name,category in modules.items():
        view='spectre' if name=='SAR_CDAC' else 'veriloga'
        top+=f'include "../../../../blocks/{category}/{name}/{view}/netlist.scs"\n'
    top+='subckt MONOTONIC_SAR ('+' '.join(ports)+')\n'
    top+='I_phase (Clks Sample VDD VSS) SAR_PHASE\nI_inv (Sample SampleB VDD VSS) SAR_INV\nI_sp (Vinp Vp Sample SampleB Gp VDD VSS) SAR_SAMPLE\nI_sn (Vinn Vn Sample SampleB Gn VDD VSS) SAR_SAMPLE\nI_bias (Bias VDD VSS) SAR_BIAS\nI_cmp (Vp Vn ClkC Outp Outn Valid Bias VDD VSS) SAR_CMP\n'
    top+='I_async (Sample Valid ClkC EOC '+' '.join(ck)+' VDD VSS) SAR_ASYNC\n'
    for i in range(9,-1,-1):
        top+=f'I_bit{i} (Outp Ck{i} Sample Q{i} Bp{i} Bn{i} VDD VSS) SAR_BIT\nI_out{i} (Q{i} EOC D{i} VDD VSS) SAR_OUT\n'
    top+='I_cdac (Vp Vn '+' '.join(bp+bn)+' VREFP VREFN) SAR_CDAC\nends MONOTONIC_SAR\n'
    write(base+'/spectre/netlist.scs',top)
    js(base+'/cell.json',dict(schema_version=1,cell='MONOTONIC_SAR',ports=ports,views={'spectre':{'netlist':'spectre/netlist.scs'}}))
    tbbase='library/testbenches/systems/monotonic_sar/tb_SAR_sine'
    tb='''simulator lang=spectre
global 0
@MODEL_SETUP@
include "../../../../../systems/monotonic_sar/MONOTONIC_SAR/spectre/netlist.scs"
parameters fin=@FIN@ tempcase=@TEMP@
simulatorOptions options temp=tempcase
VDD (VDD 0) vsource type=pwl wave=[0 0 10n 1.8]
VSS (VSS 0) vsource dc=0
VCM (VCM 0) vsource dc=0.9
VREFP (VREFP 0) vsource dc=1.8
VREFN (VREFN 0) vsource dc=0
VinP (Vinp 0) vsource type=sine dc=0.9 ampl=0.802125844320371 freq=fin
VinN (Vinn 0) vsource type=sine dc=0.9 ampl=-0.802125844320371 freq=fin
Vclock (Clks 0) vsource type=pulse val0=0 val1=1.8 delay=20n rise=20p fall=20p width=1.98n period=4n
'''
    tb+='I_adc ('+' '.join(ports)+') MONOTONIC_SAR\n'
    for i in range(10):tb+=f'CL{i} (D{i} VSS) capacitor c=10f\n'
    tb+='tran tran stop=5.50u\nsaveOptions options save=selected\n'
    tb+='save Vinp Vinn Clks '+ ' '.join(f'D{i}' for i in range(10))+' EOC I_adc.Sample I_adc.ClkC I_adc.Valid I_adc.Outp I_adc.Outn I_adc.Vp I_adc.Vn VDD:p VREFP:p VCM:p Vclock:p\n'
    write(tbbase+'/spectre/netlist.scs',tb)
    js(tbbase+'/cell.json',dict(schema_version=1,cell='tb_SAR_sine',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
    fbase='regression/systems/monotonic_sar/flows/behavioral'
    flow=dict(schema_version=1,id='sar_behavioral',testbench=tbbase+'/spectre/netlist.scs',process=None,
        conditions=[dict(id=f'k{k}',tokens={'FIN':k*50e6/256,'TEMP':25},cell_views={n:('spectre' if n=='SAR_CDAC' else 'veriloga') for n in modules},enrichment=False) for k in (3,51)],
        simulator=dict(arguments=['-64','+preset=ax'],threads=8,timeout_s=600,analyses='Transient 5.50 us, 256 contiguous conversions after 16 startup cycles',precision={'preset':'AX'}),
        measurement=dict(kind='sar',bits=10,n=256,discard_cycles=16,read_offset_s=14e-9,logic_low_v=.18,logic_high_v=1.62,expected_period_s=20e-9,behavioral_alignment=True,lsb_v=3.6/1024),
        criteria={'sample_count':{'min':256,'max':256},'invalid_bits':{'max':0},'incomplete_conversions':{'max':0},'comparison_count_errors':{'max':0},'code_mismatches':{'max':0},'period_error_s':{'max':1e-12},'sndr_db':{'min':57.0}})
    js(fbase+'/flow.json',flow)
    write(fbase+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
    write(fbase+'/measure.py','from regression.systems.monotonic_sar.measure import measure_sar\n')
    for p in ('regression/systems/monotonic_sar/flows/__init__.py',fbase+'/__init__.py'):write(p,'')
    js('config/processes/tsmc18.json',dict(schema_version=1,id='tsmc18',technology_library='tsmc18',model_sections={c:[c+'_lib','pre_simu'] for c in ('tt','ss','ff')},nominal=dict(vdd_v=1.8,temperature_c=25),enrichment=dict(adapter='tsmc18_primitive',reference_libraries=['tsmc18','analogLib','basic'],device_map='config/processes/tsmc18_device_map.txt',callbacks='config/processes/tsmc18_callbacks.json',timeout_s=300)))
    project=json.loads((ROOT/'project.json').read_text());project['flows']=[fbase+'/flow.json'];js('project.json',project)

if __name__=='__main__':main()

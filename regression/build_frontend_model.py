"""Ideal charge-domain model for the tightly coupled sampler/CDAC group."""
from regression.systems.monotonic_sar.build_behavioral import write,js
from regression.common.project import ROOT,read_json

def main():
    ports=['Vinp','Vinn','Sample','SampleB','Vp','Vn']+[f'Bp{i}' for i in range(9,0,-1)]+[f'Bn{i}' for i in range(9,0,-1)]+['VREFP','VREFN','VDD','VSS']
    weights=read_json(ROOT/'config/architecture.json')['weights']
    terms={side:' + '.join([f'{w}*V(B{side}{i},VSS)' for i,w in zip(range(9,0,-1),weights)]+['V(VREFP,VSS)']) for side in ('p','n')}
    va='''`include "constants.vams"
`include "disciplines.vams"
// Charge is stored at the falling sampling edge. DAC changes conserve it.
module SAR_FRONTEND_va('''+','.join(ports)+''');
inout '''+','.join(ports)+''';
electrical '''+','.join(ports)+''';
integer tracking;
real qp,qn,bp,bn,blend;
analog begin
'''
    va+=f' bp={terms["p"]};\n bn={terms["n"]};\n'
    va+=' @(initial_step) begin tracking=0;qp=512*(V(Vinp,VSS)-V(VREFP,VSS));qn=512*(V(Vinn,VSS)-V(VREFP,VSS));end\n'
    va+=' @(cross(V(Sample,VSS)-0.9,+1)) tracking=1;\n'
    va+=' @(cross(V(Sample,VSS)-0.9,-1)) begin qp=512*V(Vinp,VSS)-bp;qn=512*V(Vinn,VSS)-bn;tracking=0;end\n'
    va+=' blend=transition(tracking,0,10p,10p);\n'
    va+=' V(Vp,VSS)<+blend*V(Vinp,VSS)+(1-blend)*(qp+bp)/512;\n V(Vn,VSS)<+blend*V(Vinn,VSS)+(1-blend)*(qn+bn)/512;\nend\nendmodule\n'
    base='library/blocks/frontend/SAR_FRONTEND'
    write(base+'/veriloga/SAR_FRONTEND.va',va)
    write(base+'/veriloga/netlist.scs','ahdl_include "SAR_FRONTEND.va"\nsubckt SAR_FRONTEND ('+' '.join(ports)+')\nI_model ('+' '.join(ports)+') SAR_FRONTEND_va\nends SAR_FRONTEND\n')
    js(base+'/cell.json',dict(schema_version=1,cell='SAR_FRONTEND',ports=ports,views={'veriloga':{'netlist':'veriloga/netlist.scs','source':'veriloga/SAR_FRONTEND.va'}}))
    top=ROOT/'library/systems/monotonic_sar/MONOTONIC_SAR/spectre/netlist.scs'
    lines=top.read_text().splitlines()
    lines=[line for line in lines if not any(s in line for s in ('/SAR_SAMPLE/','/SAR_CDAC/','I_sp (','I_sn (','I_cdac ('))]
    lines.insert(1,'include "../../../../blocks/frontend/SAR_FRONTEND/veriloga/netlist.scs"')
    lines.insert(-1,'I_frontend ('+' '.join(ports)+') SAR_FRONTEND')
    write(str(top.relative_to(ROOT)),'\n'.join(lines)+'\n')
    flowpath='regression/systems/monotonic_sar/flows/behavioral/flow.json';flow=read_json(ROOT/flowpath)
    for c in flow['conditions']:
        c['cell_views'].pop('SAR_SAMPLE',None);c['cell_views'].pop('SAR_CDAC',None)
        c['cell_views']['SAR_FRONTEND']='veriloga'
    flow['criteria']['step_node_error_max_v']={'max':.01*3.6/1024}
    js(flowpath,flow)

if __name__=='__main__':main()

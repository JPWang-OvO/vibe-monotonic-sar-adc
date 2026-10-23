"""Initial TSMC180 implementation; dimensions are design inputs, not acceptance."""
from math import ceil
from regression.systems.monotonic_sar.build_behavioral import write,js
from regression.common.project import ROOT,read_json

def mos(name,nodes,model,w,l=.18,nf=None):
    nf=max(1,ceil(w/8)) if nf is None else nf
    return f'{name} ({nodes}) {model} w={w:.12g}u l={l:.12g}u nf={nf} m=1\n'

def std(name):return f'include "../../../../support/standard_cells/{name}/spectre/netlist.scs"\n'

def save(category,name,ports,body,includes=''):
    base=f'library/blocks/{category}/{name}'
    net='simulator lang=spectre\n// MOS D G S B; Spectre W = CDF wf = total width; CDF w = W/nf.\n'+includes
    net+='subckt '+name+' ('+' '.join(ports)+')\n'+body+'ends '+name+'\n'
    write(base+'/transistor/netlist.scs',net)
    meta=ROOT/(base+'/cell.json')
    record=read_json(meta) if meta.exists() else dict(schema_version=1,cell=name,ports=ports,views={})
    assert record['ports']==ports,(name,record['ports'],ports)
    record['views']['transistor']={'netlist':'transistor/netlist.scs'};js(base+'/cell.json',record)

def main():
    save('bias','SAR_BIAS',['Bias','VDD','VSS'],
        mos('Mp_diode','Bias Bias VDD VDD','pch',8,.36)+
        mos('Mn_sink','Bias VDD VSS VSS','nch',1.8,2)+
        'C_bias (Bias VSS) capacitor c=100f\n')
    buf='parameters scale=1\n'
    buf+='Mn (Z A VSS VSS) nch w=2u l=180n nf=1 m=scale\nMp (Z A VDD VDD) pch w=4u l=180n nf=1 m=scale\n'
    save('logic','SAR_DRIVE',['A','Z','VDD','VSS'],buf)
    drive='include "../../../logic/SAR_DRIVE/transistor/netlist.scs"\n'
    save('logic','SAR_INV',['A','Z','VDD','VSS'],
        'I_b0 (A N0 VDD VSS) SAR_DRIVE scale=1\nI_b1 (N0 N1 VDD VSS) SAR_DRIVE scale=8\nI_b2 (N1 Z VDD VSS) SAR_DRIVE scale=64\n',drive)
    invstd=std('INVD1BWP7T')
    biasports=['Vp','Vn','ClkC','Outp','Outn','Valid','Bias','VDD','VSS']
    body=mos('Mp_bias','BiasDrain Bias VDD VDD','pch',16,.36,nf=2)
    body+=mos('Mp_clock','Tail ClkC BiasDrain VDD','pch',16,nf=4)
    body+=mos('Mp_input_p','Xp Vp Tail VDD','pch',8,nf=2)+mos('Mp_input_n','Xn Vn Tail VDD','pch',8,nf=2)
    body+=mos('Mn_latch_p','Xp Xn VSS VSS','nch',4)+mos('Mn_latch_n','Xn Xp VSS VSS','nch',4)
    body+=mos('Mn_reset_p','Xp ClkC VSS VSS','nch',4)+mos('Mn_reset_n','Xn ClkC VSS VSS','nch',4)
    body+='I_outp (Xp Outp VDD VSS) INVD1BWP7T\nI_outn (Xn Outn VDD VSS) INVD1BWP7T\nI_valid (Outp Outn ValidRaw VDD VSS) ND2D1BWP7T\nI_vb0 (ValidRaw ValidB VDD VSS) SAR_DRIVE scale=1\nI_vb1 (ValidB Valid VDD VSS) SAR_DRIVE scale=4\n'
    save('comparator','SAR_CMP',biasports,body,invstd+std('ND2D1BWP7T')+drive)
    delay=''
    for i in range(6):delay+=f'I_d{i} ({"A" if i==0 else "N"+str(i-1)} {"Z" if i==5 else "N"+str(i)} VDD VSS) INVD1BWP7T\n'
    save('logic','SAR_DELAY',['A','Z','VDD','VSS'],delay,invstd)
    incdelay='include "../../../logic/SAR_DELAY/transistor/netlist.scs"\n'
    delay4=''
    for i in range(4):delay4+=f'I_d{i} ({"A" if i==0 else "N"+str(i-1)} {"Z" if i==3 else "N"+str(i)} VDD VSS) INVD1BWP7T\n'
    save('logic','SAR_DELAY4',['A','Z','VDD','VSS'],delay4,invstd)
    incdelay4='include "../../../logic/SAR_DELAY4/transistor/netlist.scs"\n'
    body=mos('Mp_charge','PorRamp VSS VDD VDD','pch',.36,5)
    body+='C_por (PorRamp VSS) capacitor c=200f\nI_por0 (PorRamp Por VDD VSS) INVD1BWP7T\nI_por1 (Por PorN VDD VSS) INVD1BWP7T\n'
    body+='I_clk0 (Clks ClksB VDD VSS) INVD1BWP7T\n'
    body+=mos('Mn_clock_slew','Clock ClksB VSS VSS','nch',.5,.72)+mos('Mp_clock_slew','Clock ClksB VDD VDD','pch',1,.72)
    body+='C_clock_slew (Clock VSS) capacitor c=20f\n'
    for i in range(5):
        name='DFSNQD1BWP7T' if i==4 else 'DFCNQD1BWP7T'
        body+=f'I_ring{i} (R{(i-1)%5} Clock PorN R{i} VDD VSS) {name}\n'
    body+='I_buffer0 (R0 SampleB_int VDD VSS) SAR_DRIVE scale=1\nI_buffer1 (SampleB_int Sample VDD VSS) SAR_DRIVE scale=16\n'
    save('clock','SAR_PHASE',['Clks','Sample','VDD','VSS'],body,invstd+std('DFCNQD1BWP7T')+std('DFSNQD1BWP7T')+drive)
    ck=[f'Ck{i}' for i in range(9,-1,-1)]
    body='I_sample_inv (Sample ClearN VDD VSS) SAR_DRIVE scale=8\n'
    for j,name in enumerate(ck):body+=f'I_seq{j} ({"VDD" if j==0 else ck[j-1]} Valid ClearN {name} VDD VSS) DFCNQD1BWP7T\n'
    body+='I_sample_guard (Sample SampleGuard VDD VSS) SAR_DELAY4\nI_feedback_delay (Valid ValidDelay VDD VSS) SAR_DELAY4\nI_run_nor (SampleGuard ValidDelay Ck0 CompareEnable VDD VSS) NR3D1BWP7T\nI_clock_drive (CompareEnable ClkC VDD VSS) SAR_DRIVE scale=1\nI_done_delay (Ck0 Done VDD VSS) SAR_DELAY\n'
    save('control','SAR_ASYNC',['Sample','Valid','ClkC','Done']+ck+['VDD','VSS'],body,std('DFCNQD1BWP7T')+std('NR3D1BWP7T')+drive+incdelay+incdelay4)
    # The DAC buffer's reference supply is explicit, separately observable.
    bitports=['Outp','Capture','Sample','Q','Bp','Bn','VDD','VSS','VREFP','VREFN']
    meta=ROOT/'library/blocks/control/SAR_BIT/cell.json'
    record=read_json(meta);record['ports']=bitports;js(str(meta.relative_to(ROOT)),record)
    va=ROOT/'library/blocks/control/SAR_BIT/veriloga/SAR_BIT.va'
    txt=va.read_text()
    if 'VREFP' not in txt:
        txt=txt.replace('Bp,Bn,VDD,VSS','Bp,Bn,VDD,VSS,VREFP,VREFN').replace('Sample,VDD,VSS;','Sample,VDD,VSS,VREFP,VREFN;')
    # The existing declaration places all electrical terminals on one line.
    txt=txt.replace('V(Bp,VSS)<+transition((1-enabled*q)*1.8','V(Bp,VREFN)<+transition((1-enabled*q)*1.8')
    txt=txt.replace('V(Bn,VSS)<+transition((1-enabled*(1-q))*1.8','V(Bn,VREFN)<+transition((1-enabled*(1-q))*1.8')
    write(str(va.relative_to(ROOT)),txt)
    write('library/blocks/control/SAR_BIT/veriloga/netlist.scs','ahdl_include "SAR_BIT.va"\nsubckt SAR_BIT ('+' '.join(bitports)+')\nparameters strength=1\nI_model ('+' '.join(bitports)+') SAR_BIT_va\nends SAR_BIT\n')
    body='parameters strength=1\nI_latch (Outp Capture Q VDD VSS) DFQD1BWP7T\nI_qbar (Q QB VDD VSS) INVD1BWP7T\nI_capture_delay (Capture CaptureD VDD VSS) SAR_DELAY4\nI_select_p (Q CaptureD BpRaw VDD VSS) ND2D1BWP7T\nI_select_n (QB CaptureD BnRaw VDD VSS) ND2D1BWP7T\n'
    for s in ('p','n'):
        for j,scale in enumerate((1,4,16,64)):
            inp=f'B{s}Raw' if j==0 else f'B{s}Buf{j-1}'
            out=f'B{s}' if j==3 else f'B{s}Buf{j}'
            supply='VREFP VREFN' if j==3 else 'VDD VSS'
            body+=f'I_buf_{s}{j} ({inp} {out} {supply}) SAR_DRIVE scale=max(1,strength*{scale})\n'
    save('control','SAR_BIT',bitports,body,std('DFQD1BWP7T')+std('ND2D1BWP7T')+invstd+incdelay4+drive)
    body='I_latch (D Done Stored VDD VSS) DFQD1BWP7T\nI_buf0 (Stored StoredB VDD VSS) SAR_DRIVE scale=1\nI_buf1 (StoredB Q VDD VSS) SAR_DRIVE scale=2\n'
    save('control','SAR_OUT',['D','Done','Q','VDD','VSS'],body,std('DFQD1BWP7T')+drive)
    body='C_boot (Ct Cb) capacitor c=80p\n'
    body+=mos('Mp_precharge','Ct Gate VDD Ct','pch_5',1024,.5)
    body+=mos('Mp_transfer','Gate Q Ct Ct','pch_5',1024,.5)
    body+=mos('Mp_start','Q Sample VDD VDD','pch_5',256,.5)
    body+=mos('Mn_start','Q Sample Cb VSS','nch_5',256,.6)
    body+=mos('Mn_trackq','Q Gate Cb VSS','nch_5',256,.6)
    body+=mos('Mn_bottom','Cb Gate Vin VSS','nch_5',2048,.6)
    body+=mos('Mn_reset_bottom','Cb SampleB VSS VSS','nch_5',2048,.6)
    # A 5 V device can reset the entire boosted gate directly.
    body+=mos('Mn_reset_gate','Gate SampleB VSS VSS','nch_5',1024,.6)
    body+=mos('Mn_sample','Top Gate Vin VSS','nch_5',1024,.6)
    save('sampling','SAR_SAMPLE',['Vin','Top','Sample','SampleB','Gate','VDD','VSS'],body)
    frontend=read_json(ROOT/'library/blocks/frontend/SAR_FRONTEND/cell.json')['ports']
    body='parameters ccross=120f\nI_sp (Vinp Vp Sample SampleB Gp VDD VSS) SAR_SAMPLE\nI_sn (Vinn Vn Sample SampleB Gn VDD VSS) SAR_SAMPLE\nC_cross_p (Gp Vn) capacitor c=ccross\nC_cross_n (Gn Vp) capacitor c=ccross\n'
    bp=[f'Bp{i}' for i in range(9,0,-1)];bn=[f'Bn{i}' for i in range(9,0,-1)]
    body+='I_cdac (Vp Vn '+' '.join(bp+bn)+' VREFP VREFN) SAR_CDAC\n'
    save('frontend','SAR_FRONTEND',frontend,body,'include "../../../sampling/SAR_SAMPLE/transistor/netlist.scs"\ninclude "../../../dac/SAR_CDAC/spectre/netlist.scs"\n')
    # Add reference rails to all bit instances while retaining current VA bindings.
    top=ROOT/'library/systems/monotonic_sar/MONOTONIC_SAR/spectre/netlist.scs'
    txt=top.read_text();lines=[]
    for line in txt.splitlines():
        if line.startswith('I_bit'):
            line=line.replace('VDD VSS) SAR_BIT','VDD VSS VREFP VREFN) SAR_BIT')
            line=line.split(' strength=')[0]+f' strength={2**(max(1,int(line[5]))-9):.12g}'
        lines.append(line)
    write(str(top.relative_to(ROOT)),'\n'.join(lines)+'\n')

if __name__=='__main__':main()

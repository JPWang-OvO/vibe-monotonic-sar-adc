"""Two cascaded bootstrap stages for 5 V sampling MOS at a 1.8 V supply.

The first stage lifts Vin by one charged capacitor voltage; the second lifts
that node again. All terminal stresses remain subject to the 5.5 V PDK limit.
This migration experiment increases overdrive without increasing drain area.
"""
from regression.build_transistors import mos,save
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
body='C_boot (Ct Cb) capacitor c=80p\n'
body+=mos('Mp_precharge','Ct Gate VDD Ct','pch_5',1024,.5)
body+=mos('Mp_transfer','Gate Q Ct Ct','pch_5',1024,.5)
body+=mos('Mp_start','Q Sample VDD Ct','pch_5',256,.5)
body+=mos('Mn_start','Q Sample Cb VSS','nch_5',256,.6)
body+=mos('Mn_trackq','Q Gate Cb VSS','nch_5',256,.6)
body+=mos('Mn_bottom','Cb Gate Vin VSS','nch_5',2048,.6)
body+=mos('Mn_reset_bottom','Cb SampleB VSS VSS','nch_5',2048,.6)
body+=mos('Mn_reset_gate','Gate SampleB VSS VSS','nch_5',1024,.6)
save('sampling','SAR_BOOST',['Vin','Gate','Sample','SampleB','VDD','VSS'],body)
high=body.replace(mos('Mn_bottom','Cb Gate Vin VSS','nch_5',2048,.6),mos('Mp_bottom','Cb SampleB Vin Ct','pch_5',2048,.5))
save('sampling','SAR_BOOST_HI',['Vin','Gate','Sample','SampleB','VDD','VSS'],high)
base='library/blocks/sampling/SAR_SAMPLE'
body='simulator lang=spectre\ninclude "../../SAR_BOOST/transistor/netlist.scs"\n'
body+='subckt SAR_SAMPLE (Vin Top Sample SampleB Gate VDD VSS)\n'
body+='I_boost1 (Vin Lift Sample SampleB VDD VSS) SAR_BOOST\nI_boost2 (Lift Gate Sample SampleB VDD VSS) SAR_BOOST\n'
body+=mos('Mn_sample','Top Gate Vin VSS','nch_5',256,.6)+'ends SAR_SAMPLE\n'
write(base+'/boost2/netlist.scs',body)
meta=read_json(ROOT/(base+'/cell.json'));meta['views']['boost2']={'netlist':'boost2/netlist.scs'};js(base+'/cell.json',meta)
high=body.replace('include "../../SAR_BOOST/transistor/netlist.scs"','include "../../SAR_BOOST/transistor/netlist.scs"\ninclude "../../SAR_BOOST_HI/transistor/netlist.scs"').replace('I_boost2 (Lift Gate Sample SampleB VDD VSS) SAR_BOOST','I_boost2 (Lift Gate Sample SampleB VDD VSS) SAR_BOOST_HI')
write(base+'/boost2p/netlist.scs',high);meta['views']['boost2p']={'netlist':'boost2p/netlist.scs'};js(base+'/cell.json',meta)
obj=read_json(ROOT/'regression/blocks/sar_sampler/flows/functional/flow.json');obj['id']='sar_sampler_boost2'
obj['conditions']=[dict(id='c'+str(c),corner='tt',tokens={'TEMP':25,'CCOMP':str(c)+'f'},cell_views={'SAR_SAMPLE':'boost2'},enrichment=True) for c in (30,60)]
obj['criteria']['bootstrap_min_v']={'min':3.0};obj['criteria']['bootstrap_max_v']={'max':3.6}
obj['simulator']['analyses']='Two-stage 5 V bootstrap: five input points; explicit 3.0 to 3.6 V gate-source target'
f='regression/blocks/sar_sampler/flows/boost2';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')
obj['id']='sar_sampler_boost2p'
for c in obj['conditions']:c['cell_views']['SAR_SAMPLE']='boost2p'
f='regression/blocks/sar_sampler/flows/boost2p';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

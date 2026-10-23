"""Include the measured sampler common-mode pedestal in comparator coverage."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
obj=read_json(ROOT/'regression/blocks/sar_cmp/flows/functional/flow.json')
points=obj['measurement']['points']+[dict(common_mode_v=-.08,differential_v=d) for d in (.00087890625,-.00087890625,.003515625,-.003515625)]
source=(ROOT/obj['testbench']).read_text();lines=[]
for line in source.splitlines():
    if line.startswith(('Vinp ','Vinn ')):
        side=line[3];sign=1 if side=='p' else -1
        values=[0,points[0]['common_mode_v']+sign*points[0]['differential_v']/2];previous=values[1]
        for j,p in enumerate(points):
            value=p['common_mode_v']+sign*p['differential_v']/2;at=50e-9+j*10e-9
            values.extend([at,previous,at+20e-12,value]);previous=value
        line=f'Vin{side} (V{side} 0) vsource type=pwl wave=['+' '.join(f'{v:.14g}' for v in values)+']'
    lines.append(line.replace('stop=252n','stop=292n'))
tb='library/testbenches/blocks/comparator/tb_SAR_CMP_extended'
write(tb+'/spectre/netlist.scs','\n'.join(lines)+'\n');js(tb+'/cell.json',dict(schema_version=1,cell='tb_SAR_CMP_extended',ports=[],views={'spectre':{'netlist':'spectre/netlist.scs'}}))
obj.update(id='sar_cmp_extended',testbench=tb+'/spectre/netlist.scs')
obj['measurement']['points']=points
obj['simulator']['analyses']='24 comparisons covering measured -80 mV to 0.9 V top-plate common mode; both polarities'
obj['conditions']=[dict(id=corner,corner=corner,tokens={'TEMP':temp},cell_views={'SAR_CMP':'fast2','SAR_BIAS':'transistor'},enrichment=True) for corner,temp in [('tt',25),('ss',125)]]
f='regression/blocks/sar_cmp/flows/extended';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

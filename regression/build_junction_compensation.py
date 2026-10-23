"""Complement the observed NMOS junction capacitance with an off PMOS.

The p-type junction has the opposite capacitance slope versus the top-plate
voltage. The PDK model and native dimensions define the compensation; no
output-code correction is present.
"""
from regression.build_transistors import mos
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
base='library/blocks/sampling/SAR_SAMPLE';meta=read_json(ROOT/(base+'/cell.json'))
source=(ROOT/(base+'/boost2p/netlist.scs')).read_text()
for width in (192,256,320):
    name='junction'+str(width)
    text=source.replace('ends SAR_SAMPLE',mos('Mp_junction','Top VDD VDD VDD','pch_5',width,.5)+'ends SAR_SAMPLE')
    write(base+'/'+name+'/netlist.scs',text);meta['views'][name]={'netlist':name+'/netlist.scs'}
js(base+'/cell.json',meta)
obj=read_json(ROOT/'regression/blocks/sar_cdac/flows/physical/flow.json');obj['id']='sar_cdac_junction'
obj['conditions']=[dict(id='p'+str(w),corner='tt',tokens={'TEMP':25,'CUNIT':'20f'},cell_views={'SAR_FRONTEND':'parametric','SAR_SAMPLE':'junction'+str(w),'SAR_CDAC':'scaled'},enrichment=True) for w in (192,256,320)]
f='regression/blocks/sar_cdac/flows/junction';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

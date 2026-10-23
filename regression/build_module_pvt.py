"""Early module checks at the four fixed final PVT combinations."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
for module in ('sar_phase','sar_cmp'):
    obj=read_json(ROOT/f'regression/blocks/{module}/flows/functional/flow.json');obj['id']=module+'_pvt'
    views=obj['conditions'][0]['cell_views']
    obj['conditions']=[dict(id=corner+'_'+('m40' if temp==-40 else 'p125'),corner=corner,tokens={'TEMP':temp},cell_views=views,enrichment=True) for corner in ('ss','ff') for temp in (-40,125)]
    f=f'regression/blocks/{module}/flows/pvt';js(f+'/flow.json',obj)
    write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

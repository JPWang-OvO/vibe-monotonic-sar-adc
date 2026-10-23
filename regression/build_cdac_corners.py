"""Measure physical charge parameters at the remaining required PVT points."""
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
obj=read_json(ROOT/'regression/blocks/sar_frontend/flows/cap24c28_loaded/flow.json');obj['id']='sar_cdac_corners'
base=obj['conditions'][0];obj['conditions']=[]
for corner,temp in [('ss',-40),('ff',-40),('ff',125)]:
    c=dict(base);c['id']=corner+('_m40' if temp<0 else '_125');c['corner']=corner;c['tokens']=dict(base['tokens'],TEMP=temp)
    c['cell_views']=dict(base['cell_views'],SAR_CMP='fast4');obj['conditions'].append(c)
f='regression/blocks/sar_cdac/flows/corners';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

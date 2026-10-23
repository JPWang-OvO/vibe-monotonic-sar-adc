"""Check the remaining physical startup and control corners before long runs."""
import copy
from regression.common.project import ROOT,read_json
from regression.systems.monotonic_sar.build_behavioral import write,js
obj=read_json(ROOT/'regression/systems/monotonic_sar/flows/physical_guard_g2/flow.json')
base=obj['conditions'][0];obj['conditions']=[];obj['id']='sar_guard_corners'
for corner,temp in [('ss',-40),('ff',-40),('ff',125)]:
    c=copy.deepcopy(base);c['id']=corner+('_m40' if temp==-40 else '_125');c['corner']=corner;c['tokens']['TEMP']=temp;obj['conditions'].append(c)
f='regression/systems/monotonic_sar/flows/physical_guard_corners';js(f+'/flow.json',obj)
write(f+'/run.py','from pathlib import Path\nfrom regression.common.runner import main\nif __name__=="__main__":main(Path(__file__).with_name("flow.json"))\n')

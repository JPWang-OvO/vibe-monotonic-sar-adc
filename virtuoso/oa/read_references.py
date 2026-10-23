"""Read the native reference symbols used for the ADC's final drawing."""
from virtuoso_bridge import VirtuosoClient
from regression.common.bridge_environment import load_bridge_environment
from regression.common.project import ROOT,read_json,artifact_root,write_json
from .native import load_reader,read_view
load_bridge_environment()
env=read_json(ROOT/'config/environments/tsmc18.local.json')
client=VirtuosoClient.from_env(profile=env['profile'],log_to_ciw=False)
load_reader(client)
out=artifact_root()/'drawing_reference'
for lib,cells in [('standard_cells',['INVD1BWP7T','ND2D1BWP7T','NR2D1BWP7T','NR3D1BWP7T','DFCNQD1BWP7T']),('tsmc18',['nmos2v','pmos2v','nmos5v','pmos5v']),('analogLib',['cap'])]:
    for cell in cells:
        circuit,drawing=read_view(client,lib,cell,'symbol')
        write_json(out/(lib+'__'+cell+'.json'),dict(circuit=circuit,drawing=drawing))
        print(lib,cell,len(circuit['terminals']),len(drawing['shapes']),flush=True)

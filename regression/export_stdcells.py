"""Capture native transistor implementations from the read-only standard library."""
from pathlib import Path
import json
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.env import load_vb_env
from virtuoso_bridge.virtuoso.skill_output import parse_sexpr
from regression.common.project import ROOT,read_json,write_json,artifact_root

def main():
    load_vb_env(explicit=str(ROOT.parent.parent/'Virtuoso Bridge/.env'))
    env=read_json(ROOT/'config/environments/tsmc18.local.json')
    names=['DFCNQD1BWP7T','DFSNQD1BWP7T','DFQD1BWP7T','INVD1BWP7T','ND2D1BWP7T','NR2D1BWP7T','NR3D1BWP7T','DEL0BWP7T']
    out=artifact_root()/'stdcell_native';out.mkdir(parents=True,exist_ok=True)
    client=VirtuosoClient.from_env(profile=env['profile'],log_to_ciw=False)
    try:
        for name in names:
            record=client.schematic.read('standard_cells',name,include_positions=False,param_filters=None)
            write_json(out/(name+'_readback.json'),record)
            query='let((c s) c=cdfGetBaseCellCDF(ddGetObj("standard_cells" "'+name+'")) s=getq(c->simInfo spectre) list(getq(s termOrder) getq(s componentName)))'
            r=client.execute_skill(query)
            if not r.ok:raise RuntimeError(r.errors)
            cdf=parse_sexpr(r.output)
            print(name,'pins',record['pins'],'CDF',cdf,flush=True)
            exported=client.schematic.export_netlist('standard_cells',name,out/name,timeout=180,netlist_only=True)
            body=Path(exported['input_file']).with_name('netlist').read_text()
            ports=cdf[0] if cdf and cdf[0] else list(record['pins'])
            base=ROOT/'library/support/standard_cells'/name
            (base/'spectre').mkdir(parents=True,exist_ok=True)
            text='// Native standard_cells schematic export. MOS terminal order: D G S B.\nsimulator lang=spectre\nsubckt '+name+' ('+' '.join(ports)+')\n'+body+'\nends '+name+'\n'
            (base/'spectre/netlist.scs').write_text(text,encoding='utf-8',newline='\n')
            write_json(base/'cell.json',dict(schema_version=1,cell=name,ports=ports,reference_library='standard_cells',views={'spectre':{'netlist':'spectre/netlist.scs'}}))
    finally:client.close()

if __name__=='__main__':main()

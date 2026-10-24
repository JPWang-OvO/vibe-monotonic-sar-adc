"""Six NMOS/PMOS geometry prototypes plus native standard-cell preservation."""
from pathlib import Path
import json
import argparse
from regression.common.project import ROOT,read_json,write_json,artifact_root
from regression.common.enrichment import enrich

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--batch',default='pdk_qualification_02');parser.add_argument('--scale',type=float,default=1.0);parser.add_argument('--five-volt',action='store_true');args=parser.parse_args()
    env=read_json(ROOT/'config/environments/tsmc18.local.json')
    process=read_json(ROOT/'config/processes/tsmc18.json')
    out=artifact_root()/args.batch;inputs=out/'inputs';inputs.mkdir(parents=True,exist_ok=False)
    source='simulator lang=spectre\nglobal 0\n'
    for s in ('tt_lib','pre_simu'):source+=f'include "{env["model_files"]["tsmc18"]}" section={s}\n'
    source+='VDD (VDD 0) vsource dc=1.8\nVg (G 0) vsource dc=.9\nVd (D 0) vsource dc=.9\n'
    source+='// MOS terminal order: D G S B\n'
    for model in (('nch_5','pch_5') if args.five_volt else ('nch','pch')):
        for name,w,nf,m in [('single',2e-6,1,1),('multi',8e-6,4,1),('multiply',6e-6,2,3)]:
            rail='0' if model.startswith('nch') else 'VDD'
            length=('600n' if model=='nch_5' else '500n') if args.five_volt else '180n'
            source+=f'M_{model}_{name} (D G {rail} {rail}) {model} w={w*args.scale} l={length} nf={nf} m={m}\n'
    # Full native export must remain exactly unchanged in effective parameters.
    native=(ROOT/'library/support/standard_cells/INVD1BWP7T/netlist/netlist.scs').read_text()
    source+=native+'\nXnative_inv (G NativeOut VDD 0) INVD1BWP7T\n'
    (inputs/'input.scs').write_text(source,encoding='utf-8',newline='\n')
    staged={'entry':'input.scs','sources':['input.scs']}
    result=enrich(inputs,staged,out/'enrichment',env,process,env['remote_runs']+'/preparation/'+args.batch,['+preset=ax','+mt=8'])
    write_json(out/'summary.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()

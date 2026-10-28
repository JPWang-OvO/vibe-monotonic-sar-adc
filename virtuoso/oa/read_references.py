"""Capture external master symbols referenced by the current OA recipes."""
import argparse
from pathlib import Path
from virtuoso_bridge import VirtuosoClient
from regression.common.bridge_environment import load_bridge_environment
from regression.common.project import ROOT, read_json, artifact_root, write_json
from .native import load_reader, read_view
from .libraries import installed_library, canonical_circuit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--environment',type=Path,default=ROOT/'config/environments/tsmc18.local.json')
    args=p.parse_args()
    masters={tuple(i['master']) for path in (ROOT/'library').rglob('circuit.json')
             for i in read_json(path)['instances'] if i['master'][0]!='MONOTONIC_SAR'}
    load_bridge_environment();env=read_json(args.environment)
    client=VirtuosoClient.from_env(profile=env['profile'],log_to_ciw=False)
    try:
        load_reader(client)
        for library,cell,view in sorted(masters):
            library_map=env.get('library_map',{})
            circuit,drawing=read_view(client,installed_library(library,library_map),cell,view)
            circuit=canonical_circuit(circuit,library_map)
            write_json(artifact_root()/'drawing_reference'/f'{library}__{cell}.json',dict(circuit=circuit,drawing=drawing))
            print(library,cell,flush=True)
    finally:client.close()


if __name__=='__main__':main()

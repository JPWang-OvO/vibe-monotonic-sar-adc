"""Apply reviewed ADC graphics, preserving any intervening native edits."""
import argparse
import re
from pathlib import Path

from regression.common.project import ROOT,artifact_root,read_json,write_json
from regression.common.bridge_environment import load_bridge_environment
from virtuoso_bridge import VirtuosoClient
from .adc_source import prepare_source,source_folders
from .adc_layout import fold_drivers
from .adc_drawing import functional_symbol,symbol_commands,svg
from .adc_build import schematic
from .native import load_reader,read_view,evaluate,q
from .comparison import circuit_semantics,drawing_objects
from .cells import capture,check


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--schematics-only',action='store_true')
    parser.add_argument('--cells',nargs='+')
    args=parser.parse_args()
    assert read_json(ROOT/'config/acceptance_results.json')['all_electrical_pass']
    env=read_json(ROOT/'config/environments/tsmc18.local.json')
    data={n:fold_drivers(d) for n,d in prepare_source(args.batch).items() if n!='INVD1BWP7T'}
    pictures={n:functional_symbol(d) for n,d in data.items()}
    if args.cells:
        assert set(args.cells)<=set(data),'Unknown cell selection'
        data={n:data[n] for n in args.cells}
    plans={n:schematic(d,pictures) for n,d in data.items()}
    load_bridge_environment();client=VirtuosoClient.from_env(profile=env['profile'],log_to_ciw=False)
    assert client.library.get('MONOTONIC_SAR').path==env['oa_library_path']
    folders=source_folders();run=artifact_root()/'oa_delivery';load_reader(client)
    previous={}
    # Read every owned native view before the first mutation. A mismatch requires
    # capturing and incorporating the user's edits before this command is used.
    for n in data:
        previous[n]={}
        for view in (('schematic',) if args.schematics_only else ('symbol','schematic')):
            circuit,drawing=read_view(client,'MONOTONIC_SAR',n,view)
            saved=read_json(folders[n]/view/'native.json')['circuit']
            assert circuit_semantics(circuit,{})==circuit_semantics(saved,{}),(n,view,'native edits')
            assert drawing_objects(drawing)==drawing_objects(read_json(folders[n]/view/'drawing.json')),(n,view,'drawing edits')
            previous[n][view]=dict(circuit=circuit,drawing=drawing)
    write_json(run/'before_redraw.json',previous)
    for n in ([] if args.schematics_only else data):
        p=pictures[n]
        with client.symbol.create('MONOTONIC_SAR',n) as editor:
            for command in symbol_commands(p):editor.add(command)
        (folders[n]/'symbol/functional.svg').write_text(svg(p),encoding='utf-8',newline='\n')
        print('Symbol',n,flush=True)
    checks=read_json(run/'redraw_checks.json') if args.cells else {}
    for n,(commands,positions) in plans.items():
        with client.schematic.create('MONOTONIC_SAR',n,timeout=180) as editor:
            for command in commands:editor.add(command)
        result=check(client,'MONOTONIC_SAR',n)
        actual=client.schematic.read('MONOTONIC_SAR',n,include_positions=True,param_filters=None)
        observed={i['name']:i for i in actual['instances']}
        for inst in data[n]['instances']:
            expected=inst['connections'];array=re.fullmatch(r'.*<(\d+):(\d+)>',inst['name'])
            if array:
                count=abs(int(array[1])-int(array[2]))+1
                expected={k:(v if ',' in v else f'<*{count}>'+v) for k,v in expected.items()}
            assert observed[inst['name']]['terms']==expected,(n,inst['name'],observed[inst['name']]['terms'],expected)
        assert set(actual['pins'])==set(data[n]['ports']),n
        messages=evaluate(client,f'let((cv result) cv=dbOpenCellViewByType("MONOTONIC_SAR" {q(n)} "schematic" "" "r") '
                          'result=mapcar(lambda((m) list(m~>severity m~>msg)) cv~>markers) dbClose(cv) result)')
        checks[n]=dict(errors=int(result[0]),warnings=int(result[1]),messages=messages or [])
        write_json(folders[n]/'schematic/circuit.json',data[n]);write_json(folders[n]/'schematic/placement.json',positions)
        write_json(run/(n+'_readback.json'),actual)
        capture(client,'MONOTONIC_SAR',folders[n],run,read_json(args.batch/'batch.json')['remote'])
        print('Schematic',n,result,flush=True)
    write_json(run/'redraw_checks.json',checks)
    exported=client.schematic.export_netlist('MONOTONIC_SAR','MONOTONIC_SAR',run/'native_netlist',simulator='spectre',netlist_only=True)
    write_json(run/'export_result.json',{k:exported[k] for k in ('source_file','source_dir','output_dir','input_file')})
    print('Redraw complete; compare the native export and review the native screenshots.',flush=True)


if __name__=='__main__':main()

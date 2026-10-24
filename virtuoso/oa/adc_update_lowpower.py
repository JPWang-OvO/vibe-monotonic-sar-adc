"""Update the accepted low-power hierarchy while retaining manual drawings.

Preparation is local. Writing requires the completed 20-case result, matching
cell views, and a fresh comparison with every maintained native view.
"""
import argparse
from copy import deepcopy
from pathlib import Path

from regression.common.project import ROOT,artifact_root,read_json,write_json
from regression.common.bridge_environment import load_bridge_environment
from virtuoso_bridge import VirtuosoClient
from .adc_source import prepare_source,source_folders,reference_libraries
from .adc_layout import fold_drivers
from .adc_lowpower_layout import layout
from .adc_schematic import schematic,symbol_anchors
from .adc_drawing import functional_symbol,symbol_commands,svg
from .adc_build import array_connections
from .native import load_reader,read_view,evaluate,execute,q
from .comparison import circuit_semantics,drawing_objects
from .replay import view_code
from .cells import check,capture


def source_key(data):
    return (data['ports'],data['parameters'],
            {i['name']:(i['master'],i['connections'],i['oa_parameters']) for i in data['instances']})


def replayable(data,old,references):
    previous={i['name']:i for i in old['instances']}
    if set(previous)!={i['name'] for i in data['instances']}:return False
    for inst in data['instances']:
        before=previous[inst['name']]
        if inst['connections']!=before['connections']:return False
        if inst['master']!=before['master']:
            # Bootstrap changes 5 V devices to 2 V devices at the same terminals.
            if data['cell']!='SAR_BOOST':return False
            a=references[inst['master'][1]]['drawing'];b=references[before['master'][1]]['drawing']
            assert {n:p[0] for n,p in symbol_anchors(a).items()}=={n:p[0] for n,p in symbol_anchors(b).items()}
            assert [s['text'] for s in a['shapes'] if s['type']=='label']==[s['text'] for s in b['shapes'] if s['type']=='label']
    return True


def parameter_replay(data,old,base):
    circuit=deepcopy(base['circuit']);previous={i['name']:i for i in old['instances']}
    current={i['name']:i for i in data['instances']}
    for native in circuit['instances']:
        if native['name'] not in current:continue
        inst=current[native['name']];native['master']=inst['master']
        keys=set(previous[native['name']]['oa_parameters'])|set(inst['oa_parameters'])
        native['properties']=[p for p in native['properties'] if p['name'] not in keys]
        native['properties'] += [dict(name=k,type='string',value=v) for k,v in inst['oa_parameters'].items()]
    return [view_code('MONOTONIC_SAR','MONOTONIC_SAR',circuit,base['drawing'],within_editor=True)],base['drawing']['instances']


def prepare(batch):
    refs=reference_libraries();folders=source_folders()
    data={n:fold_drivers(d) for n,d in prepare_source(batch).items() if n not in refs}
    bases={n:{'circuit':read_json(folders[n]/'schematic/native.json')['circuit'],
              'drawing':read_json(folders[n]/'schematic/drawing.json')} for n in data}
    old={n:read_json(folders[n]/'schematic/circuit.json') for n in data}
    references={p.stem:read_json(p) for p in (artifact_root()/'lowpower_oa_preparation/reference_symbols').glob('*.json')}
    masters={n:read_json(f/'symbol/drawing.json') for n,f in folders.items() if (f/'symbol/drawing.json').exists()}
    masters.update({n:r['drawing'] for n,r in references.items()})
    plans={};modes={}
    for n,d in data.items():
        if source_key(d)==source_key(old[n]):continue
        if replayable(d,old[n],references):
            plans[n]=parameter_replay(d,old[n],bases[n]);modes[n]='preserve drawing'
        else:
            plans[n]=schematic(d,bases[n],masters,{},layout=layout(d,bases[n]),qualified=True,functional_routes=False)
            modes[n]='route changed topology'
    symbols={n:functional_symbol(data[n]) for n in ('SAR_SAMPLE','SAR_FRONTEND','SAR_PHASE','SAR_INV','SAR_FAST_SEQ','SAR_HANDSHAKE')}
    for n,picture in symbols.items():
        actual=symbol_anchors(masters[n])
        assert all(tuple(picture.pins[k]['xy'])==tuple(v[0]) for k,v in actual.items()),(n,'Pin geometry changed')
    return data,old,bases,plans,symbols,modes


def cdf_update(cell,old,new):
    changed={k for k in old if old[k]!=new.get(k)}
    added={k:v for k,v in new.items() if v!=old.get(k)}
    if not changed and not added:return ''
    code=[f'let((cdf p) cdf=cdfGetBaseCellCDF(ddGetObj("MONOTONIC_SAR" {q(cell)}))',
          'unless(cdf error("Expected existing base CDF"))']
    for k in changed:
        code += [f'p=car(setof(item cdf~>parameters item~>name=={q(k)}))',
                 f'unless(p error("Missing old CDF parameter: {k}"))',
                 f'unless(p~>defValue=={q(old[k])} error("CDF default changed since capture: {k}"))',
                 'cdfDeleteParam(p)']
    for k,v in added.items():
        code.append(f'cdfCreateParam(cdf ?name {q(k)} ?prompt {q(k)} ?type "string" ?defValue {q(v)} ?parseAsNumber "yes" ?parseAsCEL "yes")')
    return '\n'.join(code+['cdfSaveCDF(cdf))'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--gate',type=Path,default=ROOT/'config/acceptance_lowpower_results.json')
    parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    data,old,bases,plans,symbols,modes=prepare(args.batch)
    run=artifact_root()/'lowpower_oa_delivery';run.mkdir(parents=True,exist_ok=True)
    write_json(run/'plan.json',dict(schematics=modes,symbols=list(symbols),unchanged=sorted(set(data)-set(plans))))
    for n,(commands,_) in plans.items():(run/(n+'.il')).write_text('\n'.join(commands),encoding='utf-8',newline='\n')
    print('Prepared',len(plans),'changed schematics;',len(data)-len(plans),'preserved unchanged',flush=True)
    if args.prepare_only:return
    gate=read_json(args.gate);batch=read_json(args.batch/'batch.json')
    assert gate['all_electrical_pass'] and gate['passed_cases']==20 and gate['dut_sources_equal']
    assert gate['cell_views']==batch['cases'][0]['sources']['cell_views']
    env=read_json(ROOT/'config/environments/tsmc18.local.json');folders=source_folders()
    load_bridge_environment();client=VirtuosoClient.from_env(profile=env['profile'],log_to_ciw=False)
    try:
        assert client.library.get('MONOTONIC_SAR').path==env['oa_library_path']
        load_reader(client);previous={}
        for n in data:
            previous[n]={}
            for view in ('schematic','symbol'):
                circuit,drawing=read_view(client,'MONOTONIC_SAR',n,view)
                saved=read_json(folders[n]/view/'native.json')['circuit']
                assert circuit_semantics(circuit,{})==circuit_semantics(saved,{}),(n,view,'Intervening native edit')
                assert drawing_objects(drawing)==drawing_objects(read_json(folders[n]/view/'drawing.json')),(n,view,'Intervening drawing edit')
                previous[n][view]=dict(circuit=circuit,drawing=drawing)
        write_json(run/'before_update.json',previous)
        for n,d in data.items():
            command=cdf_update(n,old[n]['parameters'],d['parameters'])
            if command:execute(client,command)
        for n,picture in symbols.items():
            with client.symbol.create('MONOTONIC_SAR',n) as editor:
                for command in symbol_commands(picture):editor.add(command)
            (folders[n]/'symbol/functional.svg').write_text(svg(picture),encoding='utf-8',newline='\n')
        checks={}
        for n,d in data.items():
            if n in plans:
                commands,positions=plans[n]
                with client.schematic.create('MONOTONIC_SAR',n,timeout=180) as editor:
                    for command in commands:editor.add(command)
            result=check(client,'MONOTONIC_SAR',n)
            actual=client.schematic.read('MONOTONIC_SAR',n,include_positions=True,param_filters=None)
            observed={i['name']:i for i in actual['instances']}
            for inst in d['instances']:
                assert observed[inst['name']]['terms']==array_connections(inst),(n,inst['name'],'Connection mismatch')
            assert set(actual['pins'])==set(d['ports']),n
            checks[n]=dict(errors=int(result[0]),warnings=int(result[1]))
            if n in plans:
                write_json(folders[n]/'schematic/circuit.json',d);write_json(folders[n]/'schematic/placement.json',positions)
            if n in plans or n in symbols:capture(client,'MONOTONIC_SAR',folders[n],run,batch['remote'])
            write_json(run/(n+'_readback.json'),actual)
            print(n,checks[n],flush=True)
        write_json(run/'checks.json',checks)
        exported=client.schematic.export_netlist('MONOTONIC_SAR','MONOTONIC_SAR',run/'native_netlist',simulator='spectre',netlist_only=True)
        write_json(run/'export_result.json',{k:exported[k] for k in ('source_file','source_dir','output_dir','input_file')})
    finally:client.close()


if __name__=='__main__':main()

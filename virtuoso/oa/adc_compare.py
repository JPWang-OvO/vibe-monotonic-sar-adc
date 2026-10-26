"""Compare the native OA export with the electrically accepted ADC hierarchy."""
import argparse
import json
import re
import os
from copy import deepcopy
from pathlib import Path

from regression.common.project import ROOT, read_json, write_json, artifact_root
from .adc_source import hierarchy, current_hierarchy, QualifiedProperties, flatten, assignments, clean_name, source_folders,prepare_source,reference_libraries
from .adc_layout import fold_drivers
from .comparison import spectre_document,expand_signals
from .native import port_order
from .adc_buses import scalar_name, FAMILIES


def native_hierarchy(text, top_ports):
    document=spectre_document(text)
    assert 'MONOTONIC_SAR' not in document['subcircuits']
    document['subcircuits']['MONOTONIC_SAR']=dict(document['top'],ports=top_ports)
    definitions={}
    for cell,data in document['subcircuits'].items():
        instances=[]
        for name,tokens in data['statements'].items():
            end=tokens.index(')')
            instances.append(dict(name=clean_name(name),nodes=tokens[1:end],model=tokens[end+1],parameters=assignments(tokens[end+2:])))
        definitions[cell]=dict(cell=cell,ports=[p for p in data['ports'] if p not in ('(',')')],
                               parameters={k:''.join(v) for k,v in data['parameters'].items()},instances=instances)
    return definitions


def main():
    p=argparse.ArgumentParser();p.add_argument('--qualification',type=Path,required=True)
    p.add_argument('--native',type=Path,required=True)
    p.add_argument('--run-id',required=True);a=p.parse_args()
    expected=current_hierarchy()
    _,enrichment=hierarchy(a.qualification)
    folders=source_folders()
    native_ports=port_order(read_json(folders['MONOTONIC_SAR']/'schematic/native.json')['circuit'])
    actual=native_hierarchy(a.native.read_text(),expand_signals(native_ports))
    assert set(expected)==set(actual),(set(expected)-set(actual),set(actual)-set(expected))
    output_map={f'D<{bit}>':f'D{bit}' for bit in range(9,-1,-1)}
    normalized=deepcopy(actual)
    for definitions in (expected,normalized):
        for cell,data in definitions.items():
            data['ports']=[scalar_name(cell,p) for p in data['ports']]
            for inst in data['instances']:
                inst['nodes']=[scalar_name(cell,n) for n in inst['nodes']]
    interfaces={name:expected[name]['ports']==normalized[name]['ports'] for name in expected}
    aliases={}
    references=reference_libraries()
    for name,data in prepare_source(a.qualification).items():
        if name in references:continue
        aliases[name]={}
        for inst in fold_drivers(data)['instances']:
            if 'array_members' not in inst:continue
            array=re.fullmatch(r'(.*)<(\d+):(\d+)>',inst['name'])
            first,last=int(array[2]),int(array[3]);step=1 if last>=first else -1
            for bit,member in zip(range(first,last+step,step),inst['array_members'],strict=True):
                aliases[name][f'{array[1]}<{bit}>']=member
    qualified=QualifiedProperties(enrichment)
    left=flatten(expected,qualified=qualified);right=flatten(normalized,instance_aliases=aliases)
    missing={str(k):v for k,v in left.items() if right.get(k)!=v}
    extra={str(k):v for k,v in right.items() if left.get(k)!=v}
    passed=all(interfaces.values()) and not missing and not extra
    result=dict(passed=passed,interfaces=interfaces,expected_primitive_groups=len(left),native_primitive_groups=len(right),
                missing_or_changed=missing,extra_or_changed=extra,native_netlist=str(a.native.resolve()),qualification_batch=str(a.qualification.resolve()),
                native_top_terminals=native_ports,output_bit_mapping=output_map,signal_families=FAMILIES)
    report=artifact_root()/a.run_id/'electrical_comparison.json'
    write_json(report,result)
    assert passed,json.dumps(result,ensure_ascii=False)[:12000]
    for name,data in actual.items():
        if name in references:continue
        ports=[p.replace('<','\\<').replace('>','\\>') if '\\' not in p else p for p in data['ports']]
        lines=['simulator lang=spectre']
        for dep in sorted({i['model'] for i in data['instances'] if i['model'] in folders}):
            relative=os.path.relpath(folders[dep]/'netlist/netlist.scs',folders[name]/'schematic').replace('\\','/')
            lines.append('include "'+relative+'"')
        lines.append('subckt '+name+' ('+' '.join(ports)+')')
        if data['parameters']:lines.append('parameters '+' '.join(k+'='+v for k,v in data['parameters'].items()))
        lines += [i['name']+' ('+' '.join(i['nodes'])+') '+i['model']+' '+
                  ' '.join(k+'='+v for k,v in i['parameters'].items()) for i in data['instances']]
        lines.append('ends '+name)
        folder=folders[name];(folder/'schematic/netlist.scs').write_text('\n'.join(line.rstrip() for line in lines)+'\n',encoding='utf-8',newline='\n')
        meta=read_json(folder/'cell.json');meta['views']['schematic']['netlist']='schematic/netlist.scs';write_json(folder/'cell.json',meta)
    final=read_json(ROOT/'config/design.json');final['status']='electrically_equivalent_oa_visual_review_pending'
    final['oa_electrical_comparison']=report.relative_to(artifact_root()).as_posix();write_json(ROOT/'config/design.json',final)
    print('Native models, effective parameters, hierarchy ports and expanded connectivity match the current source.')


if __name__=='__main__':main()

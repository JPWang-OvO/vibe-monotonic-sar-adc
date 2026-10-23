"""Compare the native OA export with the electrically accepted ADC hierarchy."""
import argparse
import json
from pathlib import Path

from regression.common.project import ROOT, read_json, write_json, artifact_root
from .adc_source import hierarchy, QualifiedProperties, flatten, assignments, clean_name, source_folders
from .comparison import spectre_document


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
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True)
    p.add_argument('--native',type=Path,required=True);a=p.parse_args()
    expected,enrichment=hierarchy(a.batch)
    actual=native_hierarchy(a.native.read_text(),expected['MONOTONIC_SAR']['ports'])
    assert set(expected)==set(actual),(set(expected)-set(actual),set(actual)-set(expected))
    interfaces={name:expected[name]['ports']==actual[name]['ports'] for name in expected}
    qualified=QualifiedProperties(enrichment)
    left=flatten(expected,qualified=qualified);right=flatten(actual)
    missing={str(k):v for k,v in left.items() if right.get(k)!=v}
    extra={str(k):v for k,v in right.items() if left.get(k)!=v}
    passed=all(interfaces.values()) and not missing and not extra
    result=dict(passed=passed,interfaces=interfaces,expected_primitive_groups=len(left),native_primitive_groups=len(right),
                missing_or_changed=missing,extra_or_changed=extra,native_netlist=str(a.native.resolve()),accepted_batch=str(a.batch.resolve()))
    write_json(artifact_root()/'oa_delivery/electrical_comparison.json',result)
    assert passed,json.dumps(result,ensure_ascii=False)[:12000]
    folders=source_folders()
    for name,data in actual.items():
        if name=='INVD1BWP7T':continue
        lines=['simulator lang=spectre','subckt '+name+' ('+' '.join(data['ports'])+')']
        if data['parameters']:lines.append('parameters '+' '.join(k+'='+v for k,v in data['parameters'].items()))
        lines += [i['name']+' ('+' '.join(i['nodes'])+') '+i['model']+' '+
                  ' '.join(k+'='+v for k,v in i['parameters'].items()) for i in data['instances']]
        lines.append('ends '+name)
        folder=folders[name];(folder/'schematic/netlist.scs').write_text('\n'.join(line.rstrip() for line in lines)+'\n',encoding='utf-8',newline='\n')
        meta=read_json(folder/'cell.json');meta['views']['schematic']['netlist']='schematic/netlist.scs';write_json(folder/'cell.json',meta)
    final=read_json(ROOT/'config/final_design.json');final['status']='electrical_pass_oa_visual_review_pending'
    final['oa_electrical_comparison']=str(artifact_root()/'oa_delivery/electrical_comparison.json');write_json(ROOT/'config/final_design.json',final)
    print('Native models, effective parameters, hierarchy ports and expanded connectivity match the accepted DUT.')


if __name__=='__main__':main()

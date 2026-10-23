"""Add native PDK parameters to staged inputs, leaving maintained sources intact."""
from pathlib import Path
import shutil
from contextlib import closing

from regression.common.project import ROOT, read_json


def enrich(inputs, staged, output, environment, process, remote, arguments):
    from virtuoso_bridge import VirtuosoClient
    from regression.common.bridge_environment import load_bridge_environment
    load_bridge_environment()
    from virtuoso_bridge.virtuoso.schematic import CdfCallbackContract
    from virtuoso_bridge.virtuoso.schematic.deck_enrichment import enrich_spectre_deck

    inputs, output = Path(inputs), Path(output)
    setup = process['enrichment']
    with closing(VirtuosoClient.from_env(profile=environment['profile'], log_to_ciw=False)) as client:
        if setup.get('adapter') == 'tsmc18_primitive':
            from regression.common.tsmc18_enrichment import enrich as primitive_enrich
            return primitive_enrich(client,inputs,staged,output,environment,process,remote,arguments)
        result = enrich_spectre_deck(
            client, inputs / staged['entry'], output,
            include_files=[inputs / name for name in staged['sources'] if name != staged['entry']],
            ref_libs=setup['reference_libraries'], dev_map_file=ROOT / setup['device_map'],
            callback_contract=CdfCallbackContract.from_mapping(read_json(ROOT / setup['callbacks'])),
            remote_work_dir=remote, spectre_arguments=arguments, timeout=setup['timeout_s'])
    shutil.copyfile(output / 'pdk.scs', inputs / 'pdk.scs')
    entry = inputs / staged['entry']
    original = entry.read_text(encoding='utf-8')
    entry.write_text('simulator lang=spectre\ninclude "pdk.scs"\n' + original, encoding='utf-8', newline='\n')
    staged['sources'].append('pdk.scs')
    return {'device_count': result.device_count, 'prototype_count': result.prototype_count,
            'change_count': len(result.changes), 'record': str(output / 'changes.json')}

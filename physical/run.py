"""Prepare existing layout inputs, run Calibre, and publish an extracted view."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess

from regression.common.project import ROOT, artifact_root, environment, identifier, read_json, write_json


def calibre(action, folder, operation=None):
    run = read_json(folder / 'run.json')
    python = Path(run['calibre_bridge_root']) / run['environment']['calibre']['python']
    command = [str(python), '-m', 'physical.calibre', action, '--run', str(folder)]
    if operation:
        command.extend(['--operation', operation])
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def prepare(env_path, target_path, run_id):
    from dotenv import load_dotenv
    from virtuoso_bridge import VirtuosoClient
    from virtuoso.oa.native import evaluate

    identifier(run_id)
    load_dotenv(ROOT / '.env', override=False)
    bridge_root = Path(os.environ['CALIBRE_BRIDGE_ROOT']).expanduser()
    if not bridge_root.is_absolute() or not bridge_root.is_dir():
        raise ValueError('CALIBRE_BRIDGE_ROOT must point to the installed tool directory')
    env, target = environment(env_path), read_json(target_path)
    process = read_json(ROOT / read_json(ROOT / 'project.json')['process'])
    folder = artifact_root() / run_id
    folder.mkdir(exist_ok=False)
    remote = env['remote_runs'] + '/' + run_id
    write_json(folder / 'run.json', {'environment': env, 'target': target, 'remote': remote,
                                    'calibre_bridge_root': str(bridge_root),
                                    'baselines': process['calibre_baselines']})
    technology = calibre('stage', folder)
    inputs = target['inputs']
    if inputs['kind'] == 'oa':
        with closing(VirtuosoClient.from_env(profile=env['profile'], log_to_ciw=False)) as vb:
            if any(op in ('lvs', 'pex') for op in target['operations']):
                cwd = evaluate(vb, 'getWorkingDir()')
                cdl = vb.schematic.export_cdl_remote(inputs['library'], inputs['cell'], remote + '/cdl',
                        cds_lib=cwd + '/cds.lib', view=inputs['source_view'])
                write_json(folder / 'cdl.export.json', cdl)
            gds = vb.layout.export_gds_remote(inputs['library'], inputs['cell'], remote + '/gds',
                    stream_map=technology['resources']['layermap'], view=inputs['layout_view'])
            write_json(folder / 'gds.export.json', gds)
        resolved = {'layout_file': gds['path'], 'layout_top_cell': inputs['cell']}
        if any(op in ('lvs', 'pex') for op in target['operations']):
            resolved.update(source_file=cdl['path'], source_top_cell=inputs['cell'])
    elif inputs['kind'] == 'files':
        resolved = {key: value for key, value in inputs.items() if key != 'kind'}
    else:
        raise ValueError('inputs.kind must be oa or files')
    for op in target['operations']:
        request = {'operation': op, 'baseline': process['calibre_baselines'][op],
                   'layout_file': resolved['layout_file'], 'layout_top_cell': resolved['layout_top_cell'],
                   'cores': target['cores']}
        if op != 'drc':
            request.update(source_file=resolved['source_file'], source_top_cell=resolved['source_top_cell'],
                           source_includes=technology['source_includes'],
                           power_names=target['power_names'], ground_names=target['ground_names'])
        if op == 'pex':
            request['pex'] = target['pex']
        write_json(folder / f'{op}.request.json', request)
    calibre('validate', folder)
    preview = [f'# {run_id}', '', f"输入：`{json.dumps(inputs, ensure_ascii=False)}`",
               f"Virtuoso profile：`{env['profile']}`；Calibre profile：`{env['calibre']['profile']}`",
               f"远端目录：`{remote}`", f"操作：{', '.join(target['operations'])}；每作业 {target['cores']} 核。", '']
    if 'pex' in target['operations']:
        preview.extend(['## PEX 设置', '', '```json', json.dumps(target['pex'], indent=2), '```', '',
                        '检查 LVS 匹配、工具结束状态、报告解析和输出端口后接入提取结果。',
                        'CALIBREVIEW 输出导入指定 OA view，再由原生 netlister 导出纳入 Git 的 PEX 网表。'])
        if target['pex']['output_format'] == 'CALIBREVIEW':
            preview.extend(['', '导入目标：`' + json.dumps(target['calibreview'], ensure_ascii=False) + '`'])
    preview.extend(['', '各操作独立提交；已提交作业按 run_id 查询。报告和原始提取保存在当前运行目录。'])
    (folder / 'preview.md').write_text('\n'.join(preview) + '\n', encoding='utf-8', newline='\n')
    return folder


def extraction_report(folder):
    report = read_json(folder / 'pex.report.json')
    if (report['run']['status'] != 'completed' or report['run']['exit_code'] != 0
            or report['parser_status'] != 'complete' or report['verification']['status'] != 'matched'
            or not report['extraction']['generated']):
        raise ValueError('PEX handoff requires successful extraction, complete parsing and matching LVS')
    return report


def import_view(folder, overwrite=False):
    from virtuoso_bridge import VirtuosoClient
    from virtuoso.oa.native import evaluate, execute, q

    run = read_json(folder / 'run.json')
    report = extraction_report(folder)
    if report['extraction']['output_format'] != 'CALIBREVIEW':
        raise ValueError('Import requires CALIBREVIEW output')
    target = run['target']['calibreview']
    technology = read_json(folder / 'technology.json')
    with closing(VirtuosoClient.from_env(profile=run['environment']['profile'], log_to_ciw=False)) as vb:
        # The vendor importer otherwise takes an active editor's library when these globals are empty.
        saved = evaluate(vb, 'list(mgc_eview_globals~>outputLibrary mgc_eview_globals~>schematicLibrary)')
        execute(vb, f'mgc_eview_globals~>outputLibrary={q(target["library"])} '
                    f'mgc_eview_globals~>schematicLibrary={q(target["schematic_library"])}')
        restore = (f'mgc_eview_globals~>outputLibrary={q(saved[0])} '
                   f'mgc_eview_globals~>schematicLibrary={q(saved[1])}')
        work = run['remote'] + '/' + datetime.now().strftime('calibreview_%Y%m%d_%H%M%S')
        try:
            result = vb.layout.import_calibreview(**target, netlist=report['extraction']['files'][0]['path'],
                    remote_dir=work, cellmap=technology['resources']['cellmap'], overwrite=overwrite)
        except TimeoutError:
            # The native API retains its context while deferred import work may still be running.
            raise
        except Exception:
            execute(vb, restore)
            raise
        else:
            execute(vb, restore)
        downloaded = vb.download_file(result['log_path'], folder / 'calibreview.log')
        if not downloaded.ok:
            raise RuntimeError(str(downloaded))
    write_json(folder / 'calibreview.json', result)
    return result


def publish(folder):
    from physical.pex import import_view as publish_spectre, publish_oa

    run = read_json(folder / 'run.json')
    report = extraction_report(folder)
    cell = ROOT / run['target']['cell_directory']
    metadata = read_json(cell / 'cell.json')
    if (report['extraction']['top_cell'] != metadata['cell']
            or set(report['extraction']['ports']) != set(metadata['ports'])):
        raise ValueError('Extracted cell and ports differ from the maintained cell interface')
    if report['extraction']['output_format'] == 'SPECTRE':
        output = publish_spectre(cell, folder / 'extracted/pex.netlist')
    else:
        from virtuoso_bridge import VirtuosoClient
        view = read_json(folder / 'calibreview.json')
        with closing(VirtuosoClient.from_env(profile=run['environment']['profile'], log_to_ciw=False)) as vb:
            exported = vb.schematic.export_netlist(view['library'], view['cell'], folder / 'oa-netlist',
                         view=view['view'], simulator='spectre', netlist_only=True)
        output = publish_oa(cell, Path(exported['output_dir']) / 'netlist')
    result = {'netlist': str(output), 'calibre_run_id': report['run']['run_id'],
              'pex_settings': run['target']['pex']}
    write_json(folder / 'published.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    prep = actions.add_parser('prepare')
    prep.add_argument('--environment', type=Path, required=True)
    prep.add_argument('--target', type=Path, required=True)
    prep.add_argument('--run-id', required=True)
    for name in ('submit', 'status', 'collect', 'cancel', 'import-view', 'publish'):
        sub = actions.add_parser(name)
        sub.add_argument('--run', type=Path, required=True)
        if name in ('submit', 'status', 'collect', 'cancel'):
            sub.add_argument('--operation', choices=('drc', 'lvs', 'pex'), required=True)
        if name == 'import-view':
            sub.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        result = str(prepare(args.environment, args.target, args.run_id))
    elif args.action == 'import-view':
        result = import_view(args.run.resolve(), args.overwrite)
    elif args.action == 'publish':
        result = publish(args.run.resolve())
    else:
        result = calibre(args.action, args.run.resolve(), args.operation)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

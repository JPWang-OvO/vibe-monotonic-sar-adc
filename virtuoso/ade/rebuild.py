"""Prepare and rebuild a flow as a native Maestro setup."""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import shlex

from regression.common.project import ROOT, artifact_root, environment, identifier, read_json, write_json
from regression.common.runner import checked
from virtuoso.oa.native import execute, evaluate, q
from .plan import compile_flow, job_timeout_s
from .native import build_tb, strings


def alist(values):
    return '(' + ' '.join('(' + q(k) + ' ' + q(str(v)) + ')' for k, v in values.items()) + ')'


def prepare(flow_path, run_id, env_path, library, library_path, workers=4):
    """Prepare native schematic settings and saved traces without running Spectre."""
    plan = compile_flow(flow_path)
    budget = read_json(ROOT/'config/run_budget.json')
    if not 1 <= workers <= budget['max_workers']:
        raise ValueError('workers must be within the project run budget')
    workers = min(workers, len(plan['points']))
    identifier(run_id); identifier(library)
    env = environment(env_path)
    if not library_path.startswith('/'):
        raise ValueError('library_path must be an absolute remote path')
    run = artifact_root() / run_id
    run.mkdir(exist_ok=False)
    remote = str(PurePosixPath(env['remote_runs']) / run_id)
    record = dict(plan=plan, environment=env, library=library, library_path=library_path,
                  remote=remote, workers=workers)
    write_json(run/'setup.json', record)
    for test in plan['tests']:
        inputs = run/test['name']/'inputs'
        inputs.mkdir(parents=True)
        (inputs/'saves.scs').write_text('simulator lang=spectre\nsave '+' '.join(plan['native_save'])+'\n',
                                      encoding='utf-8', newline='\n')
    preview = [f'# {run_id}', '', f'Flow: `{plan["flow"]}`',
               f'OA: `{library}/{plan["cell"]}/maestro`',
               f'Tests: {len(plan["tests"])}; corners: {len(plan["corners"])}; points: {len(plan["points"])}',
               f'Precision: {plan["simulator"]["precision"]}; threads/job: {plan["simulator"]["threads"]}',
               f'Maximum jobs: {workers}',
               f'ICRP job timeout: {job_timeout_s(plan)} seconds (aggregate condition budget)',
               '', '| Case | Test | Corner | Variables | Criteria |', '|---|---|---|---|---|']
    for point in plan['points']:
        preview.append(f'| {point["id"]} | {point["test"]} | {point["corner"]} | {point["variables"]} | {point["criteria"]} |')
    (run/'preview.md').write_text('\n'.join(preview)+'\n', encoding='utf-8', newline='\n')
    return run


def configure(client, record, session):
    plan, remote, env = record['plan'], record['remote'], record['environment']
    mae = client.maestro
    for test in plan['tests']:
        name = test['name']
        mae.create_test(name, lib=record['library'], cell=plan['cell'], session=session)
        analysis = dict(test['analysis'])
        if 'noisefmax' in analysis:
            analysis['tranNoise'] = 'Transient Noise'
        mae.set_analysis(name, 'tran', options=alist(analysis), session=session)
        definitions = strings(remote+'/'+name+'/inputs/'+file for file in ('saves.scs',))
        mae.set_env_option(name, options='(("switchViewList" ("spectre" "schematic")) '
                           '("stopViewList" ("spectre")) ("modelFiles" nil) '
                           '("definitionFiles" '+definitions+') ("cmd64bit" t) '
                           '("userCmdLineOption" "-format psfascii") '
                           '("simExecName" '+q(env['spectre'])+'))', session=session)
        mae.set_sim_option(name, options='(("temp" "temperature"))', session=session)
        for variable, values in test['variables'].items():
            mae.set_var(variable, ','.join(map(str, values)), type_name='test',
                        type_value='('+q(name)+')', session=session)
        execute(client, f'''let((th) th=maeGetTestSession({q(name)} ?session {q(session)})
            asiSetHighPerformanceOptionVal(th 'uniMode "Spectre X")
            asiSetHighPerformanceOptionVal(th 'spectreXPreset {q(plan['simulator']['precision']['preset'])})
            asiSetHighPerformanceOptionVal(th 'spectreXMtOption "Manual")
            asiSetHighPerformanceOptionVal(th 'spectreXNumThreads {q(str(plan['simulator']['threads']))})
            asiSetKeepOptionVal(th 'save "selected")
            asiSetKeepOptionVal(th 'simOutputFormat "psf"))''')
        for signal in plan['tb']['save']:
            if '.' not in signal and ':' not in signal:
                mae.add_output(signal, name, output_type='net', signal_name='/'+signal, session=session)
    for corner in plan['corners']:
        mae.setup_corner(corner['name'], variables={'temperature': str(corner['temperature'])}, session=session)
        for index, section in enumerate(corner['model_sections']):
            execute(client, f'''let((corn model)
                corn=axlGetCorner(axlGetMainSetupDB({q(session)}) {q(corner['name'])})
                model=axlPutModel(corn {q('process_'+str(index))})
                axlSetModelFile(model {q(env['model_files'][plan['process']])})
                axlSetModelSection(model {q(section)}))''')
    execute(client, f'axlSetNominalCornerEnabled(axlGetMainSetupDB({q(session)}) nil)')
    mae.set_current_run_mode('Single Run, Sweeps and Corners', session=session)
    mae.set_job_control_mode('Local', session=session)
    execute(client, f'''let((policy) policy=maeGetJobPolicy(?session {q(session)})
        policy->name={q(record['library']+'_'+plan['cell'])}
        policy->maxjobs={q(str(record['workers']))}
        policy->runtimeout={q(str(job_timeout_s(plan)))}
        maeSetJobPolicy(policy ?session {q(session)}))''')
    mae.save_setup(record['library'], plan['cell'], session=session)


def rebuild(client, run):
    record = read_json(run/'setup.json')
    plan, library = record['plan'], record['library']
    expected = compile_flow(ROOT/plan['flow'])
    if plan != expected:
        raise ValueError('Flow changed since prepare; prepare a new run')
    if library not in client.library.list():
        raise ValueError('Target library must already exist: ' + library)
    info = client.library.get(library)
    resolved = checked(client.ssh_runner.run_command(shlex.join(['readlink', '-f', record['library_path']]))).strip()
    if info.path != resolved:
        raise ValueError('Target library path differs from requested path')
    for test in plan['tests']:
        remote = record['remote']+'/'+test['name']+'/inputs'
        checked(client.ssh_runner.run_command(shlex.join(['mkdir', '-p', remote])))
        for source in (run/test['name']/'inputs').iterdir():
            result = client.upload_file(source, remote+'/'+source.name)
            if not result.ok:
                raise RuntimeError(str(result))
    write_json(run/'tb_readback.json', build_tb(client, library, plan['cell'], plan['tb']))
    session = client.maestro.open_session(library, plan['cell'])
    try:
        configure(client, record, session)
    finally:
        client.maestro.close_session(session)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preview', 'prepare', 'rebuild'))
    parser.add_argument('--flow', type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--environment', type=Path)
    parser.add_argument('--library')
    parser.add_argument('--library-path')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.action == 'preview':
        plan = compile_flow(args.flow)
        write_json(artifact_root()/identifier(args.run_id)/'plan.json', plan)
        print(f'{len(plan["tests"])} tests, {len(plan["corners"])} corners, {len(plan["points"])} points')
        return
    from regression.common.bridge_environment import load_bridge_environment
    load_bridge_environment()
    if args.action == 'prepare':
        print(prepare(args.flow, args.run_id, args.environment, args.library, args.library_path, args.workers))
    else:
        from virtuoso_bridge import VirtuosoClient
        run = artifact_root()/identifier(args.run_id)
        record = read_json(run/'setup.json')
        with VirtuosoClient.from_env(profile=record['environment']['profile'], log_to_ciw=False) as client:
            rebuild(client, run)
        print(run)


if __name__ == '__main__':
    main()

"""Run a saved Maestro setup and measure its explicitly bound history remotely."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import re
import shlex
import tarfile

from regression.common.project import ROOT, artifact_root, identifier, read_json, write_json
from regression.common.logs import audit
from regression.common.measure import measure
from .verify import verify_point, same_value


def measure_point(task):
    point, raw, output = task
    result = measure(point, raw, log_path=raw/'spectre.out')
    write_json(output, result)
    return {k: result[k] for k in ('metrics', 'checks', 'functional_pass', 'performance_pass')}


def process_results(setup_path, history_path, output):
    record, history = read_json(setup_path), read_json(history_path)
    plan = record['plan']
    directory = Path(history['results_root'])/history['history']
    reports, seen, measurements = [], set(), []
    for test in plan['tests']:
        for raw in sorted(directory.glob('[0-9]*/'+test['name']+'/psf')):
            variables = dict(re.findall(r'"([^"]+)"\s+"variable"\s*\(\s*([^\s)]+)',
                                       (raw/'variables_file').read_text()))
            text = (raw.parent/'netlist/input.scs').read_text()
            sections = re.findall(r'\bsection="?([\w]+)', text)
            corners = [c for c in plan['corners'] if c['model_sections'] == sections
                       and same_value(str(c['temperature']), variables.get('temp', ''))]
            if len(corners) != 1:
                raise ValueError('Cannot map native PVT to one flow corner: '+str(raw))
            corner = corners[0]
            candidates = [p for p in plan['points'] if p['test'] == test['name']
                          and p['corner'] == corner['name']
                          and all(same_value(str(v), variables.get(k, '')) for k, v in p['variables'].items())]
            if len(candidates) != 1 or candidates[0]['id'] in seen:
                raise ValueError('Native sweep point is missing, extra or duplicated: '+str(raw))
            point = dict(candidates[0]); seen.add(point['id'])
            point['waveform_names'] = {native.replace('\\', ''): source
                for source, native in zip(plan['tb']['save'], plan['native_save']) if native != source}
            verify_point(plan, test, corner, text, record['remote'], record['library'])
            command = (raw.parent/'netlist/runSimulation').read_text()
            if f'+mt={plan["simulator"]["threads"]}' not in command:
                raise ValueError('Native command does not request the flow thread count')
            if '+preset='+plan['simulator']['precision']['preset'].lower() not in command:
                raise ValueError('Native command does not request the flow accuracy preset')
            log = (raw/'spectre.out').read_text(errors='replace')
            log_audit = audit(log)
            item = dict(case=point['id'], test=test['name'], corner=corner['name'],
                        variables=point['variables'], history=history['history'],
                        execution_pass=(raw/'.simDone').exists() and log_audit['clean_completion'],
                        log_audit=log_audit, native_netlist_pass=True, remote_waveforms=str(raw))
            if item['execution_pass'] and log_audit['pass']:
                detail = output.resolve().parent/'cases'/(point['id']+'.json')
                item['remote_measurement'] = str(detail)
                measurements.append((len(reports), point, raw, detail))
            reports.append(item)
    if measurements:
        with ProcessPoolExecutor(max_workers=min(record['workers'], len(measurements))) as pool:
            results = pool.map(measure_point, [task[1:] for task in measurements])
            for (index, _, _, _), result in zip(measurements, results):
                reports[index].update(result, measurement_pass=True)
    for item in reports:
        item['pass'] = bool(item['execution_pass'] and item['log_audit']['pass']
                            and item.get('measurement_pass') and item.get('functional_pass')
                            and item.get('performance_pass') is not False)
    missing = sorted({p['id'] for p in plan['points']} - seen)
    report = dict(history=history['history'], cases=reports, not_run=missing,
                  data_processing='server', waveforms_downloaded=False,
                  pass_=not missing and all(r['pass'] for r in reports))
    write_json(output, report)
    return report


def start(client, run):
    from virtuoso.oa.native import execute, evaluate, q
    record = read_json(run/'setup.json')
    if not read_json(run/'verification.json')['pass_']:
        raise ValueError('Verify the saved setup before running')
    # An exclusive receipt prevents a second launch after an uncertain reply.
    with (run/'history.json').open('x', encoding='utf-8') as stream:
        json.dump({'state': 'dispatching'}, stream)
    # Bridge's open_gui_session closes other Maestro windows, including jobs
    # still running there. Open only this target and retain the other sessions.
    title = f"{record['library']} {record['plan']['cell']} maestro"
    windows = [w for w in client.list_windows() if title in w['name']]
    if windows:
        if len(windows) != 1 or 'Editing:' not in windows[0]['name']:
            raise ValueError('Target Maestro must have one editable GUI session')
        session = evaluate(client, f'''let((s) foreach(w hiGetWindowList()
            when(w->windowNum == {int(windows[0]['num'])} s=axlGetWindowSession(w))) s)''')
    else:
        session = evaluate(client, f'axlGetWindowSession(deOpenCellView('
                           f'{q(record["library"])} {q(record["plan"]["cell"])} '
                           '"maestro" "maestro" nil "a"))')
    client.maestro.save_setup(record['library'], record['plan']['cell'], session=session)
    root = evaluate(client, f'axlGetResultsLocation(axlGetMainSetupDB({q(session)}))')
    marker = record['remote']+'/maestro.done'
    callback = '_msar_done_'+identifier(run.name)
    execute(client, f'procedure({callback}(session runID) system({q("touch "+shlex.quote(marker))}))')
    history = client.maestro.run_simulation(session=session, callback=callback, timeout=120).strip('"')
    if not re.fullmatch(r'Interactive\.\d+', history):
        raise RuntimeError('Maestro did not return an Interactive history: '+history)
    receipt = dict(state='running', session=session, history=history, results_root=root, marker=marker)
    write_json(run/'history.json', receipt)
    return receipt


def collect(client, run):
    from regression.common.runner import checked
    record, history = read_json(run/'setup.json'), read_json(run/'history.json')
    status = client.ssh_runner.run_command(shlex.join(['test', '-f', history['marker']]))
    if status.returncode == 1:
        return {'state': 'running', 'history': history['history']}
    checked(status)
    if (run/'summary.json').exists():
        return read_json(run/'summary.json')
    bundle = run/'measurement.tar.gz'
    with tarfile.open(bundle, 'w:gz') as archive:
        for path in sorted((ROOT/'regression').rglob('*.py')):
            if not path.name.startswith('test_'):
                archive.add(path, arcname=path.relative_to(ROOT).as_posix())
        for relative in ('virtuoso/__init__.py', 'virtuoso/ade/__init__.py',
                         'virtuoso/ade/run.py', 'virtuoso/ade/verify.py', 'virtuoso/ade/plan.py'):
            archive.add(ROOT/relative, arcname=relative)
        for name in ('setup.json', 'history.json'):
            archive.add(run/name, arcname=name)
    remote = record['remote']+'/measurement'
    checked(client.ssh_runner.run_command(shlex.join(['mkdir', '-p', remote])))
    checked(client.ssh_runner.upload(bundle, remote+'/measurement.tar.gz'))
    checked(client.ssh_runner.run_command(shlex.join(['tar', '-xzf', remote+'/measurement.tar.gz', '-C', remote])))
    command = 'cd '+shlex.quote(remote)+' && '+shlex.join([
        record['environment']['server_python'], '-m', 'virtuoso.ade.run', 'process',
        '--setup', 'setup.json', '--history', 'history.json', '--output', 'summary.json'])
    result = client.ssh_runner.run_command(command, timeout=900)
    (run/'measurement.log').write_text(result.stdout+result.stderr, encoding='utf-8')
    checked(result)
    checked(client.ssh_runner.download(remote+'/summary.json', run/'summary.json'))
    return read_json(run/'summary.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify', 'start', 'collect', 'process'))
    parser.add_argument('--run-id')
    parser.add_argument('--setup', type=Path)
    parser.add_argument('--history', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'process':
        report = process_results(args.setup, args.history, args.output)
    else:
        from regression.common.bridge_environment import load_bridge_environment
        from virtuoso_bridge import VirtuosoClient
        load_bridge_environment()
        run = artifact_root()/identifier(args.run_id)
        record = read_json(run/'setup.json')
        with VirtuosoClient.from_env(profile=record['environment']['profile'], log_to_ciw=False) as client:
            if args.action == 'verify':
                from .verify import verify
                report = verify(client, run)
            elif args.action == 'start':
                report = start(client, run)
            else:
                report = collect(client, run)
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases', 'native_netlists')}, indent=2))


if __name__ == '__main__':
    main()

"""Prepare a reviewable batch, submit once, and collect scalar results and logs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import shlex
import shutil
import tarfile

from regression.common.project import ROOT, read_json, write_json, environment, artifact_root, identifier
from regression.common.sources import stage


def prepare(flow_paths, env_path, batch_id, workers=1):
    identifier(batch_id)
    if workers < 1:
        raise ValueError("workers must be positive")
    env = environment(env_path)
    budget = read_json(ROOT / 'config/run_budget.json')
    if workers > budget['max_workers']:
        raise ValueError('Worker count exceeds project resource limit')
    destination = artifact_root() / batch_id
    destination.mkdir(exist_ok=False)
    remote = str(PurePosixPath(env["remote_runs"]) / batch_id)
    process = read_json(ROOT / read_json(ROOT / "project.json")["process"])
    cases = []
    for flow_path in flow_paths:
        flow_path = Path(flow_path).resolve()
        flow = read_json(flow_path)
        for condition in flow["conditions"]:
            case_id = identifier(flow["id"] + "__" + condition["id"])
            if any(c["id"] == case_id for c in cases):
                raise ValueError("Duplicate case ID " + case_id)
            local_case = destination / "cases" / case_id
            tokens = dict(condition["tokens"])
            tokens["MODEL_SETUP"] = ""
            if flow["process"]:
                model = env["model_files"][flow["process"]]
                tokens["MODEL_SETUP"] = "\n".join(
                    f'include "{model}" section={s}' for s in process["model_sections"][condition["corner"]])
            staged = stage(ROOT / flow["testbench"], ROOT, local_case / "inputs", tokens,
                           cell_views=condition["cell_views"])
            sim = flow["simulator"]
            if sim['threads'] != 8 or '+preset=ax' not in sim['arguments']:
                raise ValueError('This project requires AX and 8 threads per simulation')
            job = PurePosixPath(remote) / "cases" / case_id
            enrichment = None
            if condition["enrichment"]:
                from regression.common.enrichment import enrich
                enrichment = enrich(local_case / "inputs", staged, local_case / "enrichment",
                                    env, process, str(PurePosixPath(env["remote_runs"]) / "preparation" / batch_id / case_id),
                                    [*sim["arguments"], f'+mt={sim["threads"]}'])
            args = [env["spectre"], staged["entry"], "-format", "psfascii",
                    "-raw", str(job / "raw"), "+log", str(job / "logs/spectre.log"),
                    *sim["arguments"], f'+mt={sim["threads"]}']
            command = args
            if env.get("cadence_setup"):
                command = ["csh", "-fc", f'source {shlex.quote(env["cadence_setup"])}; exec {shlex.join(args)}']
            case = {"id": case_id, "flow": flow_path.relative_to(ROOT).as_posix(),
                    "testbench": flow["testbench"], "condition": condition, "sources": staged,
                    "simulator": sim, "command": command, "timeout_s": sim["timeout_s"],
                    "measurement": flow["measurement"], "criteria": flow["criteria"],
                    "enrichment": enrichment}
            cases.append(case)
            write_json(local_case / "settings.json", case)
    batch = {"schema_version": 1, "batch_id": batch_id, "environment": env,
             "remote": remote, "workers": min(workers, len(cases)), "cases": cases,
             "batch_timeout_s": min(sum(c["timeout_s"] for c in cases) + 60,
                 int(datetime.fromisoformat(budget['deadline_utc'].replace('Z','+00:00')).timestamp()-datetime.now(timezone.utc).timestamp()-budget['collect_reserve_seconds'])),
             "deadline_utc": budget['deadline_utc'],
             "failure_policy": "Stop new jobs on execution/log/measurement error; finish running jobs and continue independent electrical failures"}
    write_json(destination / "batch.json", batch)
    for package in ("regression/__init__.py", "regression/common/__init__.py",
                    "regression/common/server.py", "regression/common/project.py",
                    "regression/common/measure.py", "regression/common/psf.py", "regression/common/logs.py",
                    "regression/systems/__init__.py", "regression/systems/monotonic_sar/__init__.py",
                    "regression/systems/monotonic_sar/measure.py",
                    "regression/systems/monotonic_sar/measure_modules.py"):
        target = destination / package
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / package, target)
    preview = [f"# {batch_id}", "", f"Profile: `{env['profile']}`", f"Remote: `{remote}`",
               f"Jobs: {len(cases)}; workers: {batch['workers']}; threads/job: {max(c['simulator']['threads'] for c in cases)}",
               "", "Each job includes its actual settings.json and staged inputs.", "",
               "| Case | Analyses | Acceptance |", "|---|---|---|"]
    for case in cases:
        preview.append(f"| {case['id']} | {case['simulator']['analyses']} | {json.dumps(case['criteria'])} |")
    preview += ["", batch["failure_policy"], "", "Waveforms and measurements remain on the server.",
                "No automatic reruns. Execution requires review of this batch and a fresh resource snapshot."]
    (destination / "preview.md").write_text("\n".join(preview) + "\n", encoding="utf-8")
    return destination


def ssh(batch):
    from virtuoso_bridge.transport.tunnel import SSHClient
    from regression.common.bridge_environment import load_bridge_environment
    load_bridge_environment()
    bridge = SSHClient.from_env(profile=batch["environment"]["profile"], keep_remote_files=True)
    return bridge.spectre_runner


def checked(result):
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def submit(folder):
    folder = Path(folder).resolve()
    batch = read_json(folder / "batch.json")
    runner = ssh(batch)
    checked(runner.run_command(shlex.join(["mkdir", "-p", batch["environment"]["remote_runs"]])))
    resource_script = batch['environment']['remote_runs'] + '/resources.py'
    checked(runner.upload(ROOT/'regression/common/resources.py',resource_script))
    snapshot=checked(runner.run_command(shlex.join([batch['environment']['server_python'],resource_script]),timeout=20))
    write_json(folder/'resources.json',json.loads(snapshot))
    checked(runner.run_command(shlex.join(["mkdir", batch["remote"]])))
    files=[path for path in sorted(folder.rglob('*')) if path.is_file()
           and '__pycache__' not in path.parts and 'enrichment' not in path.relative_to(folder).parts
           and path.name!='submission_bundle.tar.gz']
    bundle=folder/'submission_bundle.tar.gz'
    with tarfile.open(bundle,'w:gz') as archive:
        for path in files:archive.add(path,arcname=path.relative_to(folder).as_posix(),recursive=False)
    checked(runner.upload(bundle,batch['remote']+'/submission_bundle.tar.gz'))
    checked(runner.run_command(shlex.join(['tar','-xzf',batch['remote']+'/submission_bundle.tar.gz','-C',batch['remote']]),timeout=30))
    command = [batch["environment"]["server_python"], "-m", "regression.common.server", "submit", batch["remote"]]
    result = checked(runner.run_command(f'cd {shlex.quote(batch["remote"])} && {shlex.join(command)}', timeout=30))
    write_json(folder / "submission.json", {"receipt": json.loads(result)})
    return result


def collect(folder):
    folder = Path(folder).resolve()
    batch = read_json(folder / "batch.json")
    runner = ssh(batch)
    state = json.loads(checked(runner.run_command(shlex.join(["cat", batch["remote"] + "/status.json"]))))
    write_json(folder / "status.json", state)
    if state["state"] in ("completed", "failed"):
        # Repeated bit traces compress well; raw PSF files are excluded explicitly.
        # summary.json already contains each complete case result. Transfer it
        # once; duplicating the per-case JSON doubled the observed slow download.
        command=f'cd {shlex.quote(batch["remote"])} && tar -czf collected.tar.gz summary.json cases/*/logs/*.log'
        checked(runner.run_command(command,timeout=30))
        archive=folder/'collected.tar.gz'
        checked(runner.download(batch['remote']+'/collected.tar.gz',archive))
        allowed={'summary.json'}
        for case in batch['cases']:
            allowed.update(f'cases/{case["id"]}/{name}' for name in ('results.json','logs/console.log','logs/spectre.log'))
        with tarfile.open(archive) as packed:
            for member in packed:
                if not member.isfile() or member.name not in allowed:
                    raise ValueError('Unexpected collection member '+member.name)
                target=folder/member.name;target.parent.mkdir(parents=True,exist_ok=True)
                with packed.extractfile(member) as source,target.open('wb') as dest:
                    shutil.copyfileobj(source,dest)
        for result in read_json(folder/'summary.json')['cases']:
            write_json(folder/'cases'/result['case']/'results.json',result)
    return state


def main(default_flow=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--flow", action="append", type=Path)
    prep.add_argument("--environment", type=Path, required=True)
    prep.add_argument("--batch-id", default="run_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    prep.add_argument("--workers", type=int, default=1)
    execute = commands.add_parser("execute")
    execute.add_argument("--batch", type=Path, required=True)
    get = commands.add_parser("collect")
    get.add_argument("--batch", type=Path, required=True)
    cancel = commands.add_parser("cancel")
    cancel.add_argument("--batch", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        paths = args.flow or ([default_flow] if default_flow else [ROOT / p for p in read_json(ROOT / "project.json")["flows"]])
        print(prepare(paths, args.environment, args.batch_id, args.workers))
    elif args.action == "execute":
        print(submit(args.batch))
    elif args.action == "collect":
        print(json.dumps(collect(args.batch)))
    else:
        batch = read_json(args.batch / "batch.json")
        command = [batch["environment"]["server_python"], "-m", "regression.common.server", "cancel", batch["remote"]]
        print(checked(ssh(batch).run_command(f'cd {shlex.quote(batch["remote"])} && {shlex.join(command)}')))


if __name__ == "__main__":
    main()

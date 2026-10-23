"""Detached server supervisor and bounded parallel controller; data stays remote."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime

from regression.common.project import read_json, write_json
from regression.common.logs import audit
from regression.common.measure import measure

MODULE = "regression.common.server"


def status(root, **fields):
    fields["updated_unix_s"] = time.time()
    temporary = root / "status.next.json"
    write_json(temporary, fields)
    temporary.replace(root / "status.json")


def terminate_group(pid):
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def run_case(root, case, stop_time):
    started = time.time()
    directory = root / "cases" / case["id"]
    raw = directory / "raw"
    logs = directory / "logs"
    raw.mkdir()
    logs.mkdir()
    command = case["command"]
    with (logs / "console.log").open("w") as stream:
        process = subprocess.Popen(command, cwd=directory / "inputs", stdout=stream,
                                   stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                   start_new_session=True)
        write_json(directory / "active.next.json", {"case": case["id"], "pid": process.pid})
        (directory / "active.next.json").replace(directory / "active.json")
        try:
            returncode = process.wait(timeout=min(case["timeout_s"], max(0.01, stop_time - time.monotonic())))
            timed_out = False
        except subprocess.TimeoutExpired:
            terminate_group(process.pid)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            returncode, timed_out = process.returncode, True
        finally:
            (directory / "active.json").unlink()
    logfile = logs / "spectre.log"
    text = logfile.read_text(errors="replace") if logfile.exists() else ""
    report = {"case": case["id"], "started_unix_s": started, "finished_unix_s": time.time(),
              "returncode": returncode, "timeout": timed_out,
              "execution_pass": returncode == 0 and not timed_out,
              "log_audit": audit(text), "log_present": logfile.exists(), "remote_waveforms": str(raw)}
    if report["execution_pass"] and report["log_audit"]["pass"]:
        try:
            report.update(measure(case, raw))
            report["measurement_pass"] = True
        except (ValueError, KeyError, OSError) as error:
            report.update(measurement_pass=False, measurement_error=str(error))
    report["pass"] = bool(report["execution_pass"] and report["log_audit"]["pass"]
                          and report.get("measurement_pass") and report.get("functional_pass"))
    write_json(directory / "results.json", report)
    return report


def control(root):
    batch = read_json(root / "batch.json")
    reports = []
    remaining_wall = datetime.fromisoformat(batch['deadline_utc'].replace('Z','+00:00')).timestamp()-time.time()-900
    if remaining_wall <= 0:
        raise ValueError('Project collection reserve has begun; no new jobs allowed')
    stop_time = time.monotonic() + min(batch["batch_timeout_s"], remaining_wall)
    remaining = iter(batch["cases"])
    stop_launching = False
    with ThreadPoolExecutor(max_workers=batch["workers"]) as pool:
        running = {}
        while True:
            while not stop_launching and len(running) < batch["workers"]:
                case = next(remaining, None)
                if case is None:
                    break
                running[pool.submit(run_case, root, case, stop_time)] = case["id"]
            if not running:
                break
            status(root, state="running", current=list(running.values()), completed=len(reports), total=len(batch["cases"]))
            finished, _ = wait(running, return_when=FIRST_COMPLETED)
            for future in finished:
                running.pop(future)
                report = future.result()
                reports.append(report)
                if not report["execution_pass"] or not report["log_audit"]["pass"] or not report.get("measurement_pass"):
                    stop_launching = True
    by_id = {r["case"]: r for r in reports}
    reports = [by_id[c["id"]] for c in batch["cases"] if c["id"] in by_id]
    result = {"batch_id": batch["batch_id"], "cases": reports,
              "not_run": [c["id"] for c in batch["cases"] if c["id"] not in by_id],
              "pass": len(reports) == len(batch["cases"]) and all(r["pass"] for r in reports),
              "data_processing": "server", "waveforms_downloaded": False}
    write_json(root / "summary.json", result)
    return 0 if result["pass"] else 1


def supervise(root):
    cancel_requested = False

    def request_cancel(signum, frame):
        nonlocal cancel_requested
        cancel_requested = True

    signal.signal(signal.SIGTERM, request_cancel)
    worker = subprocess.Popen([sys.executable, "-m", MODULE, "control", str(root)],
                              cwd=root, stdin=subprocess.DEVNULL, start_new_session=True)
    write_json(root / "supervisor.json", {"pid": os.getpid(), "controller_pid": worker.pid})

    while worker.poll() is None and not cancel_requested:
        time.sleep(0.1)
    if cancel_requested:
        terminate_group(worker.pid)
        try:
            worker.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(worker.pid, signal.SIGKILL)
            worker.wait()
        for active in root.glob("cases/*/active.json"):
            terminate_group(read_json(active)["pid"])
        time.sleep(1)
        for active in root.glob("cases/*/active.json"):
            try:
                os.killpg(read_json(active)["pid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
            active.unlink()
        status(root, state="cancelled")
        write_json(root / "event.json", {"batch_id": read_json(root / "batch.json")["batch_id"], "state": "cancelled"})
        return
    code = worker.returncode
    for active in root.glob("cases/*/active.json"):
        # A controller crash cannot leave its simulator occupying the worker slot.
        pid = read_json(active)["pid"]
        terminate_group(pid)
        time.sleep(1)
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        active.unlink()
    summary = root / "summary.json"
    state = "completed" if code == 0 else ("failed" if summary.exists() else "controller_error")
    status(root, state=state, returncode=code)
    write_json(root / "event.json", {"batch_id": read_json(root / "batch.json")["batch_id"], "state": state})


def submit(root):
    current=read_json(root/'batch.json')
    configured=current['workers']
    for sibling in root.parent.iterdir():
        if sibling==root or not (sibling/'batch.json').exists() or not (sibling/'status.json').exists():
            continue
        if read_json(sibling/'status.json')['state'] in ('accepted','running'):
            configured+=read_json(sibling/'batch.json')['workers']
    if configured>14:
        raise ValueError('Concurrent project workers would exceed 14')
    # Exclusive receipt protects a batch from duplicate submission after a lost reply.
    with (root / "accepted.json").open("x") as stream:
        json.dump({"accepted_unix_s": time.time()}, stream)
    status(root, state="accepted")
    with (root / "supervisor.log").open("w") as stream:
        process = subprocess.Popen([sys.executable, "-m", MODULE, "supervise", str(root)],
                                   cwd=root, stdin=subprocess.DEVNULL, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    print(json.dumps({"accepted": True, "supervisor_pid": process.pid, "remote": str(root)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("submit", "supervise", "control", "cancel"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "submit":
        submit(root)
    elif args.action == "supervise":
        supervise(root)
    elif args.action == "control":
        try:
            return control(root)
        except Exception:
            (root / "controller-error.log").write_text(traceback.format_exc())
            raise
    else:
        if read_json(root / "status.json")["state"] in ("completed", "failed", "controller_error", "cancelled"):
            raise ValueError("Batch already terminal")
        os.kill(read_json(root / "supervisor.json")["pid"], signal.SIGTERM)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

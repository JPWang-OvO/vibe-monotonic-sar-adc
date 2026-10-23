"""Read the selected CIW and execution host before writing libraries or running jobs."""
import argparse
import json
import os
from pathlib import Path
import shlex

from regression.common.project import artifact_root, ROOT, read_json, write_json


def main():
    from virtuoso_bridge import VirtuosoClient
    from virtuoso_bridge.transport.tunnel import SSHClient
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--remote-run", required=True)
    args = parser.parse_args()
    client = VirtuosoClient.from_env(profile=args.profile, log_to_ciw=False)
    bridge = SSHClient.from_env(profile=args.profile, keep_remote_files=True)
    runner = bridge.spectre_runner
    from regression.common.runner import checked
    checked(runner.run_command(shlex.join(["mkdir", "-p", args.remote_run])))
    script = args.remote_run + "/resource_probe.py"
    checked(runner.upload(ROOT / "regression/common/resources.py", script))
    resource = json.loads(checked(runner.run_command(shlex.join(["python3", script]))))
    process = read_json(ROOT / read_json(ROOT / "project.json")["process"])
    report = {"profile": args.profile, "ciw_workdir": client.execute_skill("getWorkingDir()").output,
              "resource": resource, "libraries": client.library.list(),
              "pdk": vars(client.library.get(process["technology_library"])),
              "cadence_setup": os.environ.get("VB_CADENCE_CSHRC_" + args.profile) or os.environ.get("VB_CADENCE_CSHRC")}
    path = artifact_root() / "environment-inspection.json"
    write_json(path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

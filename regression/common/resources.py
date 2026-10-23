"""Read a one-second Linux CPU and memory snapshot; emits no environment secrets."""
import json
import os
from pathlib import Path
import socket
import time


def cpu():
    fields = list(map(int, Path("/proc/stat").read_text().splitlines()[0].split()[1:9]))
    return sum(fields), fields[3], fields[4]


def main():
    before = cpu()
    started = time.monotonic()
    time.sleep(1)
    after = cpu()
    total = after[0] - before[0]
    mem = {line.split(":")[0]: line.split(":")[1].strip() for line in Path("/proc/meminfo").read_text().splitlines()}
    physical = set()
    for block in Path("/proc/cpuinfo").read_text().split("\n\n"):
        fields = dict(line.split(":", 1) for line in block.splitlines() if ":" in line)
        fields = {key.strip(): value.strip() for key, value in fields.items()}
        if "physical id" in fields and "core id" in fields:
            physical.add((fields["physical id"], fields["core id"]))
    print(json.dumps({"unix_s": time.time(), "host": socket.gethostname(),
        "logical_cpus": os.cpu_count(), "affinity_cpus": len(os.sched_getaffinity(0)),
        "physical_cores": len(physical) or None, "sample_s": time.monotonic()-started,
        "cpu_busy_percent": 100 * (total - (after[1]-before[1]) - (after[2]-before[2])) / total,
        "iowait_percent": 100 * (after[2]-before[2]) / total,
        "mem_available": mem["MemAvailable"], "load_average": os.getloadavg(),
        "scheduler_quota": "unknown", "license_capacity": "unknown"}))


if __name__ == "__main__":
    main()

"""Project identity and runtime paths; no machine-specific defaults."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def identifier(value):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value):
        raise ValueError(f"Expected an identifier, got {value!r}")
    return value


def artifact_root(root=ROOT):
    project_id = identifier(read_json(root / "project.json")["project_id"])
    configured = os.environ.get("VIRTUOSO_BRIDGE_ARTIFACTS_DIR", "").strip()
    if configured:
        base = Path(configured).expanduser()
        if not base.is_absolute():
            raise ValueError("VIRTUOSO_BRIDGE_ARTIFACTS_DIR must be absolute")
        result = base / project_id
    else:
        result = root / "artifacts"
    result.mkdir(parents=True, exist_ok=True)
    return result.resolve()


def environment(path):
    data = read_json(path)
    for key in ("profile", "remote_runs", "server_python", "spectre"):
        if not data.get(key) or "<" in data[key]:
            raise ValueError(f"Configure environment field {key!r}")
    for key in ("remote_runs", "server_python", "spectre"):
        if not data[key].startswith("/"):
            raise ValueError(f"{key} must be an absolute remote Linux path")
    if data.get("cadence_setup") is not None and not data["cadence_setup"].startswith("/"):
        raise ValueError("cadence_setup must be an absolute path or null for the SSH login environment")
    return data

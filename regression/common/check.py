"""Check maintained ownership, interfaces, references and documentation offline."""
from __future__ import annotations

import re
from pathlib import Path

from regression.common.project import ROOT, read_json
from regression.common.plans import load_plan
from regression.common.variants import sources as variant_sources
from regression.common.measure import MEASUREMENT_MODULES
from virtuoso.oa.comparison import spectre_document,expand_signals


def check(root=ROOT):
    problems, cells = [], {}
    for path in sorted((root / "library").rglob("cell.json")):
        record = read_json(path)
        name = record["cell"]
        if name in cells:
            problems.append(f"Duplicate cell identity {name}")
        cells[name] = path
        if path.parent.name != name:
            problems.append(f"Directory/cell mismatch: {path}")
        for view, files in record["views"].items():
            for kind, relative in files.items():
                target = path.parent / relative
                if not target.is_file():
                    problems.append(f"Missing {view}/{kind}: {target}")
            if "netlist" in files and record["ports"]:
                source = path.parent / files["netlist"]
                parsed = spectre_document(source.read_text(encoding="utf-8"))
                if name not in parsed['subcircuits'] or (view != 'pex' and set(parsed['subcircuits']) != {name}):
                    problems.append(f"Expected own cell definition (PEX may include extracted child subcircuits): {source}")
                else:
                    ports = [token.replace('\\<','<').replace('\\>','>') for token in parsed["subcircuits"][name]["ports"]]
                    if ports != ["(", *expand_signals(record["ports"]), ")"]:
                        problems.append(f"Ordered ports differ: {source}")
        recipe = path.parent / "schematic/circuit.json"
        if recipe.exists():
            spec = read_json(recipe)
            if spec["ports"] != record["ports"]:
                problems.append(f"Recipe ports differ: {recipe}")
            native_path = path.parent / "schematic/native.json"
            if native_path.exists():
                native = read_json(native_path)["circuit"]
                instances = {row["name"]: row for row in native["instances"]}
                for row in spec["instances"]:
                    saved = instances[row["name"]]
                    connections=row['connections']
                    array=re.fullmatch(r'.*<(\d+):(\d+)>',row['name'])
                    if array:
                        count=abs(int(array[1])-int(array[2]))+1
                        connections={k:(v if len(expand_signals([v]))>1 else f'<*{count}>'+v)
                                     for k,v in connections.items()}
                    if row["master"] != saved["master"] or connections != saved["connections"]:
                        problems.append(f"Native/recipe circuit differs: {recipe}:{row['name']}")
    project = read_json(root / "project.json")
    for relative in project['flows'] + project['studies']:
        path = root / relative
        if not path.with_name('run.py').is_file():
            problems.append(f'Missing plan entry: {path}')
        kind = load_plan(path)['measurement']['kind']
        module = MEASUREMENT_MODULES[kind]
        if not (root / (module.replace('.', '/') + '.py')).is_file():
            problems.append(f'Missing measurement module: {module}')
    for flow in project["flows"]:
        path = root / flow
        config = load_plan(path)
        if not (root / config["testbench"]).is_file():
            problems.append(f"Missing TB in {path}")
        if not config["criteria"]:
            problems.append(f"Missing criteria: {path}")
        if config.get('baseline'):
            baseline = read_json(root/config['baseline'])
            if {r['condition'] for r in baseline['cases']} != {c['id'] for c in config['conditions']}:
                problems.append(f'Baseline conditions differ: {path}')
    for study in project['studies']:
        plan = load_plan(root/study)
        for condition in plan['conditions']:
            variant_sources(condition, root)
    registered = set(project['flows'])
    actual = {p.relative_to(root).as_posix() for p in (root/'regression').rglob('flow.json')}
    if registered != actual:
        problems.append(f'Unregistered or missing flows: {registered ^ actual}')
    for path in root.rglob("*.md"):
        if any(p in (".git", "artifacts", ".pytest_cache") for p in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        if path.is_relative_to(root / "docs"):
            if not text.startswith("---\n"):
                problems.append(f"Missing frontmatter: {path}")
            else:
                header = text.split("---", 2)[1]
                for key in ("title", "type", "status", "last_reviewed", "authoritative_sources"):
                    if not re.search(rf"(?m)^{key}:", header):
                        problems.append(f"Missing {key}: {path}")
        for match in re.finditer(r'\]\(([^)]+)\)', text):
            link = match.group(1).strip("<>").split("#",1)[0]
            if not link or "://" in link or link.startswith("mailto:"):
                continue
            if not (path.parent / link).exists():
                problems.append(f"Broken link: {path.relative_to(root)} -> {link}")
    return problems


def main():
    problems = check()
    for problem in problems:
        print(problem)
    print(f"Project checks: {len(problems)} issue(s)")
    return bool(problems)


if __name__ == "__main__":
    raise SystemExit(main())

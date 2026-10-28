"""Capture native views, publish design parameters, and verify a replay."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import shlex

from regression.common.project import ROOT, read_json, write_json, artifact_root, environment
from regression.common.units import numeric
from .native import execute, evaluate, q, load_reader, read_view
from .replay import view_code, write_and_load
from .comparison import circuit_semantics, drawing_objects, spectre_document, design_equivalent
from .libraries import installed_library, canonical_circuit


def check(client, library, cell):
    result = evaluate(client, f'let((cv result) cv=dbOpenCellViewByType({q(library)} {q(cell)} "schematic" "" "a") '
                      'result=schCheck(cv) dbSave(cv) dbClose(cv) result)')
    if not result or int(result[0]):
        raise ValueError(f"Check/Save errors: {result}")
    return result


def assert_spec(client, library, folder, *, library_map=None):
    spec = read_json(folder / "schematic/circuit.json")
    actual = client.schematic.read(library, spec["cell"], include_positions=True, param_filters=None)
    instances = {row["name"]: row for row in actual["instances"]}
    for expected in spec["instances"]:
        row = instances[expected["name"]]
        lib, cell, view = expected["master"]
        if [row["lib"], row["cell"], row["view"]] != [installed_library(lib, library_map), cell, view]:
            raise ValueError("Master mismatch for " + row["name"])
        if row["terms"] != expected["connections"]:
            raise ValueError(f"Connection mismatch: {row['name']}: {row['terms']}")
        for key, value in expected["parameters"].items():
            actual_key = "fingers" if key == "nf" else key
            if numeric(row["params"][actual_key]) != numeric(value):
                raise ValueError(f"Parameter mismatch: {row['name']}.{key}")
    if set(actual["pins"]) != set(spec["ports"]):
        raise ValueError("Native interface differs from maintained ports")
    return actual


def capture(client, library, folder, run, remote, *, library_map=None):
    metadata = read_json(folder / "cell.json")
    cell = metadata["cell"]
    load_reader(client)
    for view in ("schematic", "symbol"):
        circuit, drawing = read_view(client, library, cell, view)
        circuit = canonical_circuit(circuit, library_map)
        write_json(folder / view / "native.json", {"schema":"native-oa-v1", "source_library":library, "circuit":circuit})
        write_json(folder / view / "drawing.json", drawing)
        files = metadata["views"].setdefault(view, {})
        files.update(native=f"{view}/native.json", drawing=f"{view}/drawing.json")
    source = remote + "/" + cell + ".cdf.il"
    execute(client, f'cdfDump({q(library)} {q(source)} ?cellName {q(cell)} ?level \'base)')
    response = client.download_file(source, folder / "cdf.il")
    if not response.ok:
        raise RuntimeError(str(response))
    if (folder / "cdf.il").read_text(encoding="utf-8").strip():
        metadata["cdf"] = "cdf.il"
    else:
        (folder / "cdf.il").unlink()
        metadata.pop("cdf", None)
    write_json(folder / "cell.json", metadata)


def export_leaf(client, library, folder, run, *, library_map=None):
    cell = read_json(folder / "cell.json")["cell"]
    assert_spec(client, library, folder, library_map=library_map)
    result = client.schematic.export_netlist(library, cell, run / "netlist" / library / cell,
                                              simulator="spectre", netlist_only=True)
    text = (Path(result["output_dir"]) / "netlist").read_text(encoding="utf-8")
    return text


def publish_leaf(client, library, folder, run, *, library_map=None):
    """Publish native connections and the declared design parameters."""
    metadata = read_json(folder / "cell.json")
    text = export_leaf(client, library, folder, run, library_map=library_map)
    document = spectre_document(text)
    spec = read_json(folder / "schematic/circuit.json")
    if document["subcircuits"] or set(document["top"]["statements"]) != {i["name"] for i in spec["instances"]}:
        raise ValueError("Expected a leaf-only native circuit export")
    statements = []
    for instance in spec["instances"]:
        name = instance["name"]
        tokens = document["top"]["statements"][name]
        head = " ".join(tokens[:tokens.index(")") + 2])
        parameters = {("multi" if key == "m" else key): value
                      for key, value in instance["parameters"].items()}
        assignments = " ".join(f"{key}={value}" for key, value in parameters.items())
        statements.append(f"{name} {head} {assignments}")
    body = "simulator lang=spectre\nsubckt " + metadata["cell"] + " (" + " ".join(metadata["ports"]) + ")\n"
    body += "\n".join(statements) + "\nends " + metadata["cell"] + "\n"
    (folder / metadata["views"]["schematic"]["netlist"]).write_text(body, encoding="utf-8", newline="\n")


def replay(client, library, folder, run, remote, *, library_map=None):
    metadata = read_json(folder / "cell.json")
    for view in ("symbol", "schematic"):
        files = metadata["views"][view]
        native = read_json(folder / files["native"])
        drawing = read_json(folder / files["drawing"])
        source_library = native["source_library"]
        code = view_code(library, source_library, native["circuit"], drawing, library_map=library_map)
        name = metadata["cell"] + "__" + view + ".il"
        write_and_load(client, code, run / name, remote + "/" + name)
    if "cdf" in metadata:
        cdf = (folder / metadata["cdf"]).read_text(encoding="utf-8")
        cdf, count = re.subn(r'(?m)^(\s*LIBRARY\s*=\s*)"' + re.escape(source_library) + '"',
                             lambda m: m[1] + q(library), cdf)
        if count != 1:
            raise ValueError("Expected one saved CDF library declaration")
        write_and_load(client, cdf, run / (metadata["cell"] + ".cdf.il"), remote + "/" + metadata["cell"] + ".cdf.il")
    return verify(client, library, folder, run, library_map=library_map)


def verify(client, library, folder, run, *, library_map=None):
    metadata = read_json(folder / "cell.json")
    check(client, library, metadata["cell"])
    load_reader(client)
    report = {"cell":metadata["cell"], "library":library, "views":[]}
    for view in ("symbol", "schematic"):
        files = metadata["views"][view]
        saved = read_json(folder / files["native"])
        circuit, drawing = read_view(client, library, metadata["cell"], view)
        circuit = canonical_circuit(circuit, library_map)
        write_json(run / (metadata["cell"] + "__" + view + "__readback.json"), {"circuit":circuit,"drawing":drawing})
        report["views"].append({"view":view,
            "electrical_equal":circuit_semantics(saved["circuit"],{}) == circuit_semantics(circuit,{library:saved["source_library"]}),
            "drawing_equal":drawing_objects(read_json(folder / files["drawing"])) == drawing_objects(drawing)})
    native_text = export_leaf(client, library, folder, run, library_map=library_map)
    expected = spectre_document((folder / metadata["views"]["schematic"]["netlist"]).read_text())["subcircuits"][metadata["cell"]]
    actual = spectre_document(native_text)["top"]
    report["netlist_equal"] = design_equivalent(expected, actual)
    report["pass"] = report["netlist_equal"] and all(row["electrical_equal"] and row["drawing_equal"] for row in report["views"])
    write_json(run / (metadata["cell"] + "__verification.json"), report)
    if not report["pass"]:
        raise ValueError(json.dumps(report))
    return report


def main():
    from virtuoso_bridge import VirtuosoClient
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "publish-netlist", "replay", "verify"))
    parser.add_argument("--cell", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--library-path", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    env = environment(args.environment)
    run = artifact_root() / args.run_id
    run.mkdir(exist_ok=True)
    remote = env["remote_runs"] + "/" + args.run_id
    client = VirtuosoClient.from_env(profile=env["profile"], log_to_ciw=False)
    from regression.common.runner import checked
    checked(client.ssh_runner.run_command(shlex.join(["mkdir", "-p", remote])))
    technology = read_json(ROOT / read_json(ROOT / "project.json")["process"])["technology_library"]
    if args.library not in client.library.list():
        checked(client.ssh_runner.run_command(shlex.join(["mkdir", "-p", str(PurePosixPath(args.library_path).parent)])))
        client.library.create(args.library, args.library_path, technology_library=technology)
    info = client.library.get(args.library)
    requested_path = checked(client.ssh_runner.run_command(shlex.join(["readlink", "-f", args.library_path]))).strip()
    if info.path != requested_path or info.technology_library != technology:
        raise ValueError(f"Library identity differs from requested path/technology: {info}")
    print({"workdir":evaluate(client,"getWorkingDir()"),"library":vars(info)})
    folder = args.cell.resolve()
    library_map = env.get("library_map", {})
    if args.action == "capture":
        capture(client, args.library, folder, run, remote, library_map=library_map)
    elif args.action == "publish-netlist":
        publish_leaf(client, args.library, folder, run, library_map=library_map)
    elif args.action == "verify":
        print(verify(client, args.library, folder, run, library_map=library_map))
    else:
        print(replay(client, args.library, folder, run, remote, library_map=library_map))


if __name__ == "__main__":
    main()

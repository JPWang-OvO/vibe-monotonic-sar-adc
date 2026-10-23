"""Publish an extracted Spectre circuit as a maintained cell view."""
import argparse
from pathlib import Path
import re

from regression.common.project import read_json, write_json
from virtuoso.oa.comparison import spectre_document


def expand_includes(netlist):
    active = set()

    def expand(path):
        path = path.resolve()
        if path in active:
            raise ValueError(f'Recursive include: {path}')
        active.add(path)
        lines = []
        for line in path.read_text(encoding='utf-8').splitlines():
            match = re.fullmatch(r'\s*include\s+"([^"]+)"\s*', line)
            if match:
                lines.append(expand(path.parent / match[1]))
            else:
                lines.append(line)
        active.remove(path)
        return '\n'.join(lines)

    return expand(Path(netlist))


def save_view(cell_folder, text):
    cell_folder = Path(cell_folder).resolve()
    metadata = read_json(cell_folder / 'cell.json')
    destination = cell_folder / 'pex/netlist.scs'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text.rstrip() + '\n', encoding='utf-8', newline='\n')
    metadata['views']['pex'] = {'netlist': 'pex/netlist.scs'}
    write_json(cell_folder / 'cell.json', metadata)
    return destination


def import_view(cell_folder, netlist):
    metadata = read_json(Path(cell_folder) / 'cell.json')
    text = expand_includes(netlist)
    cell = metadata['cell']
    pattern = rf'(?im)^subckt\s+{re.escape(cell)}\s*\(([^)]*)\)'
    declarations = list(re.finditer(pattern, text))
    if len(declarations) != 1:
        raise ValueError(f'Expected one declaration of {cell}')
    ports = declarations[0][1].split()
    if sorted(ports) != sorted(metadata['ports']):
        raise ValueError(f'Extracted ports {ports} differ from {metadata["ports"]}')
    text = re.sub(pattern, f'subckt {cell} ({" ".join(metadata["ports"])})', text)
    return save_view(cell_folder, text)


def publish_oa(cell_folder, netlist):
    """Wrap the native top-level circuit while retaining its full parameters."""
    metadata = read_json(Path(cell_folder) / 'cell.json')
    source = expand_includes(netlist)
    original = spectre_document(source)
    cell = metadata['cell']
    if cell in original['subcircuits']:
        raise ValueError(f'Native export already contains a subcircuit named {cell}')

    # Keep native statement text, including continued lines and signed exponents.
    directives, children, top = [], [], []
    depth = 0
    for line in source.splitlines():
        command = line.strip().split(maxsplit=1)[0] if line.strip() else ''
        if command == 'subckt':
            depth += 1
        if depth:
            children.append(line)
            if command == 'ends':
                depth -= 1
        elif command in ('simulator', 'global', 'include', 'ahdl_include'):
            directives.append(line)
        else:
            top.append(line)
    lines = ['simulator lang=spectre', *directives, *children,
             f'subckt {cell} ({" ".join(metadata["ports"])})', *top, 'ends ' + cell]
    text = '\n'.join(lines) + '\n'
    published = spectre_document(text)
    for field in ('parameters', 'statements'):
        if published['subcircuits'][cell][field] != original['top'][field]:
            raise ValueError(f'Native top-level {field} changed during publication')
    if {k: v for k, v in published['subcircuits'].items() if k != cell} != original['subcircuits']:
        raise ValueError('Native child subcircuits changed during publication')
    return save_view(cell_folder, text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cell', type=Path, required=True)
    parser.add_argument('--netlist', type=Path, required=True)
    args = parser.parse_args()
    print(import_view(args.cell, args.netlist))


if __name__ == '__main__':
    main()

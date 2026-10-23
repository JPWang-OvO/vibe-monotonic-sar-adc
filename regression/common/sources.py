"""Resolve cell views and stage a flat Spectre dependency package."""
from __future__ import annotations

import re
from pathlib import Path

from regression.common.project import read_json

INCLUDE = re.compile(r'^\s*(include|ahdl_include)\s+"([^"]+)"(.*)$')


def stage(entry, root, output, substitutions, *, cell_views):
    root, output = Path(root).resolve(), Path(output).resolve()
    visiting, visited, sources = set(), {}, []

    def choose(path):
        relative = path.relative_to(root)
        metadata = path.parent.parent / 'cell.json'
        if not metadata.exists():
            return path, relative
        cell = read_json(metadata)
        entries = {(metadata.parent / files['netlist']).resolve()
                   for files in cell['views'].values() if 'netlist' in files}
        if path not in entries or cell['cell'] not in cell_views:
            return path, relative
        view = cell_views[cell['cell']]
        selected = cell['views'][view]
        alternative = (metadata.parent / selected['netlist']).resolve()
        relative = alternative.relative_to(root)
        declaration = rf'(?im)^subckt\s+{re.escape(cell["cell"])}\s*\(([^)]*)\)'
        old = re.search(declaration, path.read_text())
        new = re.search(declaration, alternative.read_text())
        if not old or not new or old.group(1).split() != new.group(1).split():
            raise ValueError(f'Ordered ports differ for {cell["cell"]} / {view}')
        return alternative, relative

    def visit(path):
        path, relative = choose(path.resolve())
        if path in visiting:
            raise ValueError(f'Include cycle at {relative}')
        if path in visited:
            return None
        visiting.add(path)
        name = '__'.join(relative.parts)
        text = path.read_text(encoding='utf-8')
        for key, value in substitutions.items():
            text = text.replace('@' + key + '@', str(value))
        missing = re.findall(r'@[A-Z][A-Z0-9_]*@', text)
        if missing:
            raise ValueError(f'Unresolved tokens in {relative}: {missing}')
        lines = []
        for line in text.splitlines():
            match = INCLUDE.match(line)
            if match:
                kind, included, suffix = match.groups()
                if included.startswith('/'):
                    lines.append(line)
                    continue
                child = visit(path.parent / included)
                if child is None:
                    continue
                line = f'{kind} "{child}"{suffix}'
            lines.append(line)
        output.mkdir(parents=True, exist_ok=True)
        (output / name).write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        visiting.remove(path)
        visited[path] = name
        sources.append(name)
        return name

    entry_name = visit(Path(entry))
    return {'entry': entry_name, 'sources': sources, 'cell_views': dict(cell_views)}

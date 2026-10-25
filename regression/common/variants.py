"""Materialize study parameter and topology changes only in staged inputs."""
import re

from regression.common.project import ROOT, read_json


def sources(condition, root=ROOT):
    edits = condition.get('source_edits', [])
    topology = condition.get('topology', {})
    if not edits and not topology:
        return {}
    cells = {read_json(p)['cell']: p.parent for p in (root / 'library').rglob('cell.json')}
    result = {}

    def source(cell):
        if cell not in result:
            result[cell] = (cells[cell] / 'netlist/netlist.scs').read_text(encoding='utf-8')
        return result[cell]

    for edit in edits:
        cell, parameter, value = edit['cell'], edit['parameter'], edit['value']
        text = source(cell)
        names = edit.get('instances', ['parameters'])
        for name in names:
            pattern = rf'(?m)^({re.escape(name)}\s+[^\n]*?\b{re.escape(parameter)}=)([^\s]+)'
            text, count = re.subn(pattern, lambda m: m[1] + value, text)
            if count != 1:
                raise ValueError(f'Expected one study target: {cell}/{name}/{parameter}, found {count}')
        result[cell] = text
    for key, stages in topology.items():
        if key != 'feedback_stages':
            raise ValueError('Unknown topology variable: ' + key)
        if not isinstance(stages, int) or stages < 2 or stages % 2:
            raise ValueError('Feedback delay requires a positive even inverter count')
        text = source('SAR_ASYNC')
        pattern = r'(?m)^I_feedback_delay__I_b\d+ .*\n'
        original = re.findall(pattern, text)
        if len(original) != 4:
            raise ValueError('Expected the current four-inverter feedback chain')
        lines = []
        for index in range(stages):
            before = 'Valid' if index == 0 else f'I_feedback_delay__N{index-1}'
            after = 'ValidDelay' if index == stages-1 else f'I_feedback_delay__N{index}'
            lines.append(f'I_feedback_delay__I_b{index} ({before} {after} VDD VSS) INVD1BWP7T\n')
        text = text.replace(''.join(original), ''.join(lines))
        result['SAR_ASYNC'] = text
    return result

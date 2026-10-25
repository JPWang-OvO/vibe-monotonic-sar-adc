"""Ordered signal families in the native ADC hierarchy."""
import re

from .comparison import expand_signals


FAMILIES = {
    'SAR_CDAC': ('Bp', 'Bn'),
    'SAR_FRONTEND': ('Bp', 'Bn'),
    'SAR_ASYNC': ('Ck',),
    'SAR_PHASE': ('R',),
    'MONOTONIC_SAR': ('D', 'Q', 'Bp', 'Bn', 'Ck'),
}


def signal_name(cell, name):
    name = name.replace('\\<', '<').replace('\\>', '>')
    reset = re.fullmatch(r'I_seq(\d+)__ResetN', name)
    if cell == 'SAR_ASYNC' and reset:
        return f'ResetN<{reset[1]}>'
    match = re.fullmatch(r'([A-Za-z_]\w*?)(\d+)', name)
    return f'{match[1]}<{match[2]}>' if match and match[1] in FAMILIES.get(cell, ()) else name


def scalar_name(cell, name):
    name = name.replace('\\<', '<').replace('\\>', '>')
    reset = re.fullmatch(r'ResetN<(\d+)>', name)
    if cell == 'SAR_ASYNC' and reset:
        return f'I_seq{reset[1]}__ResetN'
    match = re.fullmatch(r'(\w+)<(\d+)>', name)
    return match[1]+match[2] if match and match[1] in FAMILIES.get(cell, ()) else name


def compact_signals(names):
    """Compress adjacent ordered bits, preserving mixed nets and broadcasts."""
    names = expand_signals(names)
    result = []; index = 0
    while index < len(names):
        first = re.fullmatch(r'(\w+)<(\d+)>', names[index])
        end = index + 1; step = None
        while first and end < len(names):
            nxt = re.fullmatch(r'(\w+)<(\d+)>', names[end])
            previous = re.fullmatch(r'(\w+)<(\d+)>', names[end-1])
            if not nxt or nxt[1] != first[1]: break
            delta = int(nxt[2])-int(previous[2])
            if abs(delta) != 1 or (step is not None and step != delta): break
            step = delta; end += 1
        result.append(f'{first[1]}<{first[2]}:{nxt_bit(names[end-1])}>' if end-index > 1 else names[index])
        index = end
    return result


def nxt_bit(name):
    return name[name.index('<')+1:-1]


def group_interfaces(definitions):
    old_ports = {n: list(d['ports']) for n, d in definitions.items()}
    groups = {n: compact_signals([signal_name(n, p) for p in ports]) for n, ports in old_ports.items()}
    for cell, data in definitions.items():
        data['ports'] = groups[cell]
        for inst in data['instances']:
            inst['nodes'] = [signal_name(cell, node) for node in inst['nodes']]
            if inst['model'] in definitions:
                model = inst['model']
                values = dict(zip([signal_name(model, p) for p in old_ports[model]], inst['nodes'], strict=True))
                inst['connections'] = {p: ','.join(compact_signals([values[n] for n in expand_signals([p])])) for p in groups[model]}
            else:
                inst['connections'] = {p: signal_name(cell, n) for p, n in inst['connections'].items()}

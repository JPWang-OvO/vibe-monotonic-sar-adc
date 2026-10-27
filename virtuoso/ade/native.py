"""Build a native TB using the existing library symbols and schematics."""
from __future__ import annotations

from regression.common.project import ROOT, read_json
from virtuoso.oa.native import evaluate, execute, q
from virtuoso.oa.comparison import expand_signals


def strings(values):
    return 'list(' + ' '.join(q(v) for v in values) + ')'


def source_properties(parameters):
    mapping = {'dc': 'vdc', 'type': 'srcType', 'delay': 'td', 'rise': 'tr',
               'fall': 'tf', 'width': 'pw', 'period': 'per', 'ampl': 'va'}
    values = {mapping.get(k, k): v for k, v in parameters.items() if k != 'wave'}
    if 'wave' in parameters:
        pairs = parameters['wave'].strip('[]').split()
        if len(pairs) % 2 or len(pairs) > 100:
            raise ValueError('analogLib vsource supports at most 50 time/value pairs')
        values['pwlEntryMethod'] = 'Time-Voltage Pairs'
        values['tvpairs'] = len(pairs) // 2
        for i in range(len(pairs) // 2):
            values[f't{i+1}'], values[f'v{i+1}'] = pairs[2*i:2*i+2]
    return values


def connections(ports, nodes):
    """Bind ordered scalar TB nodes to the existing symbol's grouped terminals."""
    if len(expand_signals(ports)) != len(nodes):
        raise ValueError('TB instance port count differs')
    result = {}; offset = 0
    for port in ports:
        width = len(expand_signals([port]))
        result[port] = ','.join('gnd!' if n == '0' else n for n in nodes[offset:offset+width])
        offset += width
    return result


def build_tb(client, library, cell, tb):
    from virtuoso_bridge.virtuoso.schematic import schematic_create_inst_by_master_name as inst
    from virtuoso.oa.adc_schematic import symbol_anchors
    from virtuoso.oa.geometry import transform, wire, label, segments, intersect

    if evaluate(client, f'ddGetObj({q(library)} {q(cell)} "schematic")'):
        raise ValueError('Destination TB view already exists: ' + cell)
    cells = {m['cell']: m for p in (ROOT/'library').rglob('cell.json') for m in [read_json(p)]}
    drawing = read_json(ROOT/'virtuoso/ade/presentation.json')[cell]
    pins, placements, properties, masters, nets = {}, {}, {}, {}, {}
    for row in tb['instances']:
        model, name = row['model'], row['name']
        master = ('analogLib', 'cap' if model == 'capacitor' else 'vsource') if model in ('vsource', 'capacitor') else (library, model)
        actual = client.symbol.read_ports(*master)
        terms = ['PLUS', 'MINUS'] if master[0] == 'analogLib' else cells[model]['ports']
        if master[0] != 'analogLib':
            if actual['termOrder'] != terms:
                raise ValueError('Existing symbol port order differs: ' + model)
            if not evaluate(client, f'ddGetObj({q(library)} {q(model)} "schematic")'):
                raise ValueError('Existing DUT schematic is missing: ' + model)
        pins[name] = symbol_anchors(dict(
            shapes=[dict(bbox=t['bbox']) for t in actual['terms']],
            pins=[dict(terminal=t['name'], figure=i) for i,t in enumerate(actual['terms'])]))
        if master[0] == 'analogLib':
            pins[name] = {term: (point, (0, 1 if term == 'PLUS' else -1))
                          for term, (point, _) in pins[name].items()}
        placements[name] = dict(xy=drawing['positions'][name], orient=drawing['rotations'].get(name, 'R0'))
        masters[name] = master
        properties[name] = source_properties(row['parameters']) if model == 'vsource' else row['parameters']
        nets[name] = connections(terms, row['nodes'])

    def anchor(name, term):
        return transform(pins[name][term][0], placements[name])

    paths, connected = [], set()
    for source, source_term, target, target_term, bends in drawing['routes']:
        net = nets[source][source_term]
        if net != nets[target][target_term]:
            raise ValueError('Presentation route joins different nets')
        points = [anchor(source, source_term), *map(tuple, bends), anchor(target, target_term)]
        points = [p for i,p in enumerate(points) if not i or p != points[i-1]]
        paths.append((net, points))
        connected.update(((source, source_term), (target, target_term)))
    for name, terms in nets.items():
        for term, net in terms.items():
            if (name, term) in connected:
                continue
            (px, py), (dx, dy) = pins[name][term]
            length = 2.5 if len(expand_signals([term])) > 1 else .5
            paths.append((net, [anchor(name, term), transform((px+length*dx, py+length*dy), placements[name])]))
    for index, (net, points) in enumerate(paths):
        for other_net, other_points in paths[:index]:
            if net != other_net and any(intersect(a,b,c,d) for a,b in segments(points) for c,d in segments(other_points)):
                raise ValueError('Presentation wires intersect: ' + net + ', ' + other_net)

    with client.schematic.create(library, cell) as schematic:
        schematic.add(inst('analogLib', 'gnd', 'symbol', 'GROUND', -6, 3, 'R0'))
        for row in tb['instances']:
            name = row['name']; place = placements[name]
            schematic.add('let((obj) obj=' + inst(*masters[name], 'symbol', name, *place['xy'], place['orient']) +
                          ' ' + ' '.join(f'dbReplaceProp(obj {q(k)} {q("int" if isinstance(v, int) else "string")} {q(v)})'
                                         for k,v in properties[name].items()) + ')')
        for net, points in paths:
            a,b = points[0:2]
            vertical = a[0] == b[0]
            x, y = (a[0]+b[0])/2, (a[1]+b[1])/2
            x, y = (x-.04375, y) if vertical else (x, y+.04375)
            text = label(x, y, net, 'lowerCenter', 'R90' if vertical else 'R0').replace('cv nil', 'cv car(wires)', 1)
            schematic.add('let((wires) wires=' + wire(points, route_style='draw', route_mode='direct') + ' ' + text + ')')
        for name, term in drawing.get('no_connect', []):
            (px, py), (dx, dy) = pins[name][term]
            end = transform((px+.5*dx, py+.5*dy), placements[name])
            schematic.add(inst('basic', 'noConn', 'symbol', 'NC_'+term, *end,
                               {(1,0): 'R90', (-1,0): 'R270', (0,1): 'R180', (0,-1): 'R0'}[(dx,dy)]))
        for x,y,text in drawing['notes']:
            schematic.add(f'schCreateNoteLabel(cv {x}:{y} {q(text)} "lowerLeft" "R0" "stick" 0.125 "normalLabel")')
    actual = client.schematic.read(library, cell, include_positions=True, param_filters=None)
    by_name = {r['name']: r for r in actual['instances']}
    for name, terms in nets.items():
        if by_name[name]['terms'] != terms:
            raise ValueError('TB native connection mismatch: ' + name)
    markers = evaluate(client, f'let((cv) cv=dbOpenCellViewByType({q(library)} {q(cell)} "schematic" "" "r") '
                       'prog1(cv~>markers~>msg dbClose(cv)))')
    if markers:
        raise ValueError('TB schematic check markers: ' + str(markers))
    return actual

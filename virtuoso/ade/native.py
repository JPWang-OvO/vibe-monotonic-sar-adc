"""Build a native TB with explicit Spectre subcircuit interfaces."""
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


def interface(client, library, metadata):
    """A stop-view symbol binds the ordered ports to the staged cell definition."""
    from virtuoso_bridge.virtuoso.symbol import (
        symbol_create_rect, symbol_create_pin, symbol_set_term_order,
        symbol_create_instance_label, symbol_create_logical_label)
    cell = metadata['cell']
    ports = expand_signals(metadata['ports'])
    if evaluate(client, f'ddGetObj({q(library)} {q(cell)} "symbol")'):
        actual = client.symbol.read_ports(library, cell)
        if actual['termOrder'] != ports:
            raise ValueError('Existing ADE interface has different port order: ' + cell)
        return ports
    height = max(1.0, (len(ports) + 1) * .25)
    with client.symbol.create(library, cell) as symbol:
        symbol.add(symbol_create_rect('device', 'drawing', 0, -height, 2, 0))
        for index, port in enumerate(ports):
            symbol.add(symbol_create_pin(port, -.25, -.25 * (index+1), direction='inputOutput'))
        symbol.add(symbol_set_term_order(ports))
        symbol.add(symbol_create_instance_label(0, .125))
        symbol.add(symbol_create_logical_label(1, -height/2))
    # The symbol stop view uses the standard Spectre subcircuit formatter.
    execute(client, f'''let((cdf)
        cdf=cdfCreateBaseCellCDF(ddGetObj({q(library)} {q(cell)}))
        cdf->simInfo=list(nil)
        cdf->simInfo->spectre=list(nil 'componentName {q(cell)}
            'termOrder {strings(ports)} 'namePrefix "")
        cdfSaveCDF(cdf))''')
    return ports


def build_tb(client, library, cell, tb):
    from virtuoso_bridge.virtuoso.schematic import (
        schematic_create_inst_by_master_name as inst,
        schematic_create_wire as wire,
        schematic_create_wire_label as wire_label,
        schematic_label_instance_term as label)
    if evaluate(client, f'ddGetObj({q(library)} {q(cell)} "schematic")'):
        raise ValueError('Destination TB view already exists: ' + cell)
    cells = {m['cell']: m for p in (ROOT/'library').rglob('cell.json') for m in [read_json(p)]}
    ports = {}
    for row in tb['instances']:
        if row['model'] not in ('vsource', 'capacitor'):
            ports[row['model']] = interface(client, library, cells[row['model']])
    with client.schematic.create(library, cell) as schematic:
        schematic.add(inst('analogLib', 'gnd', 'symbol', 'GROUND', -3, 0, 'R0'))
        x, y = 0., 0.
        for index, row in enumerate(tb['instances']):
            model, name = row['model'], row['name']
            if model == 'vsource':
                master, terms = ('analogLib', 'vsource'), ['PLUS', 'MINUS']
                values = source_properties(row['parameters'])
            elif model == 'capacitor':
                master, terms = ('analogLib', 'cap'), ['PLUS', 'MINUS']
                values = row['parameters']
            else:
                master, terms = (library, model), ports[model]
                values = row['parameters']
            if len(terms) != len(row['nodes']):
                raise ValueError('TB instance port count differs: ' + name)
            schematic.add('let((obj) obj=' + inst(*master, 'symbol', name, x, y, 'R0') +
                          ' ' + ' '.join(f'dbReplaceProp(obj {q(k)} {q("int" if isinstance(v, int) else "string")} {q(v)})'
                                         for k, v in values.items()) + ')')
            for pin_index, (term, net) in enumerate(zip(terms, row['nodes'])):
                net = 'gnd!' if net == '0' else net
                if model in ports:
                    pin_y = y - .25 * (pin_index + 1)
                    schematic.add(wire([(x - .25, pin_y), (x - .75, pin_y)],
                                       route_style='draw', route_mode='direct'))
                    schematic.add(wire_label(x - .75, pin_y, net,
                                             justification='lowerRight', rotation='R0'))
                else:
                    schematic.add(label(name, term, net))
            y -= max(2., (len(terms) + 2) * .25)
            if index % 6 == 5:
                x += 6.; y = 0.
    actual = client.schematic.read(library, cell, include_positions=False, param_filters=None)
    by_name = {r['name']: r for r in actual['instances']}
    for row in tb['instances']:
        terms = ['PLUS', 'MINUS'] if row['model'] in ('vsource', 'capacitor') else ports[row['model']]
        if by_name[row['name']]['terms'] != dict(zip(terms, ['gnd!' if n == '0' else n for n in row['nodes']])):
            raise ValueError('TB native connection mismatch: ' + row['name'])
    return actual

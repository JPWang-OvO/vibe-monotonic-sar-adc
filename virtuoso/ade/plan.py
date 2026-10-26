"""Compile registered flows into Maestro tests, PVT corners and variable sweeps."""
from __future__ import annotations

from itertools import product
from pathlib import Path
import re

from regression.common.plans import load_plan
from regression.common.project import ROOT, read_json, identifier


def assignments(text):
    pairs = re.findall(r'(\w+)=(\[[^\]]*\]|[^\s]+)', text)
    remainder = re.sub(r'(\w+)=(\[[^\]]*\]|[^\s]+)', '', text).strip()
    if remainder:
        raise ValueError(f'Unsupported TB assignment: {remainder}')
    return dict(pairs)


def testbench(path):
    """Read the fixed TB subset used by the registered transient flows."""
    result = {'instances': [], 'parameters': {}, 'save': [], 'analysis': {}}
    for raw in Path(path).read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith(('//', 'simulator lang=', 'global ', 'include ', '@MODEL_SETUP@')):
            continue
        if line.startswith('parameters '):
            result['parameters'].update(assignments(line[11:]))
        elif line.startswith('tran tran '):
            result['analysis'] = assignments(line[10:].replace('@NOISE@', ''))
        elif line.startswith(('simulatorOptions options ', 'saveOptions options ')):
            # Temperature comes from the corner; saves come from the fixed TB.
            expected = {'temp': '@TEMP@'} if '@TEMP@' in line else {'temp': 'tempcase'}
            values = assignments(line.split(' options ', 1)[1])
            if values not in (expected, {'save': 'selected'}):
                raise ValueError(f'Unsupported TB options: {line}')
        elif line.startswith('save '):
            result['save'].extend(line[5:].split())
        else:
            match = re.fullmatch(r'(\w+)\s+\(([^)]*)\)\s+(\w+)\s*(.*)', line)
            if not match:
                raise ValueError(f'Unsupported fixed TB statement: {line}')
            name, nodes, model, params = match.groups()
            result['instances'].append(dict(name=name, nodes=nodes.split(), model=model,
                                            parameters=assignments(params)))
    if not result['analysis'] or not result['instances']:
        raise ValueError('Expected a transient TB with instances')
    return result


def compile_flow(path):
    path = Path(path).resolve()
    project = read_json(ROOT / 'project.json')
    relative = path.relative_to(ROOT).as_posix()
    if relative not in project['flows']:
        raise ValueError('ADE rebuild requires a registered flow')
    flow = load_plan(path)
    setup = flow['ade']
    tb = testbench(ROOT / flow['testbench'])
    process = read_json(ROOT / project['process'])
    corner_map = {}
    for condition in flow['conditions']:
        temperature = condition['tokens']['TEMP']
        name = identifier(condition['corner'] + '_' + str(temperature).replace('-', 'm').replace('.', 'p'))
        corner_map[name] = dict(name=name, process=condition['corner'], temperature=temperature,
                                model_sections=process['model_sections'][condition['corner']])
    tests, assigned, points = [], set(), []
    for definition in setup['tests']:
        selected = [c for c in flow['conditions']
                    if all(c[k] == v for k, v in definition['when'].items())]
        if not selected:
            raise ValueError('Empty ADE test: ' + definition['name'])
        variables = {name: sorted({c['tokens'][token] for c in selected})
                     for name, token in setup.get('sweep_variables', {}).items()}
        first = selected[0]
        noise = first['tokens'].get('NOISE', '')
        for c in selected:
            if c['id'] in assigned:
                raise ValueError('Case assigned to more than one test: ' + c['id'])
            assigned.add(c['id'])
            if (c['cell_views'], c['enrichment'], c['tokens'].get('NOISE', '')) != (
                    first['cell_views'], first['enrichment'], noise):
                raise ValueError('Different view/enrichment/analysis settings require separate tests')
            known = {'TEMP', 'NOISE', *setup.get('sweep_variables', {}).values()}
            if set(c['tokens']) - known:
                raise ValueError('Unmapped TB tokens: ' + str(set(c['tokens']) - known))
        test = dict(name=identifier(definition['name']), variables=variables,
                    analysis={**tb['analysis'], **assignments(noise)},
                    cell_views=first['cell_views'], enrichment=first['enrichment'])
        tests.append(test)
        # Require the selected cases to be exactly the native corner × sweep product.
        expanded = []
        for corner, values in product(corner_map.values(), product(*variables.values())):
            var = dict(zip(variables, values))
            matches = [c for c in selected if c['corner'] == corner['process']
                       and c['tokens']['TEMP'] == corner['temperature']
                       and all(c['tokens'][setup['sweep_variables'][key]] == val for key, val in var.items())]
            if len(matches) != 1:
                raise ValueError(f'Corner/sweep product differs from flow: {test["name"]}, {corner["name"]}, {var}')
            c = matches[0]
            expanded.append(c['id'])
            points.append(dict(id=flow['id'] + '__' + c['id'], test=test['name'],
                               corner=corner['name'], variables=var, condition=c,
                               measurement=flow['measurement'], criteria=c['criteria'],
                               simulator=flow['simulator']))
        if set(expanded) != {c['id'] for c in selected}:
            raise ValueError('Unrepresented cases in test ' + test['name'])
    if assigned != {c['id'] for c in flow['conditions']}:
        raise ValueError('ADE tests do not cover every flow condition')
    return dict(schema_version=1, flow=relative, id=flow['id'],
                cell=identifier('ade_' + flow['id']),
                testbench=flow['testbench'], tb=tb, process=flow['process'],
                tests=tests, corners=list(corner_map.values()), points=points,
                simulator=flow['simulator'])

"""Expand specification flows and optimization studies into concrete cases."""
from copy import deepcopy
from itertools import product
from pathlib import Path

from regression.common.project import ROOT, read_json, identifier


def conditions(flow):
    defaults = flow['condition_defaults']
    result = []
    for row in flow['conditions']:
        condition = deepcopy(defaults)
        condition.update(deepcopy(row))
        condition['tokens'] = {**defaults.get('tokens', {}), **row['tokens']}
        criteria = deepcopy(flow['criteria'])
        for rule in flow.get('criteria_rules', []):
            if all(condition[key] == value for key, value in rule['when'].items()):
                criteria.update(deepcopy(rule['criteria']))
        condition['criteria'] = criteria
        result.append(condition)
    return result


def load_plan(path, selected=None):
    path = Path(path).resolve()
    config = read_json(path)
    if path.name == 'flow.json':
        plan = deepcopy(config)
        plan['conditions'] = conditions(config)
    elif path.name == 'study.json':
        base = read_json(ROOT / config['flow']) if 'flow' in config else config['experiment']
        plan = deepcopy(base)
        plan['id'] = config['id']
        plan['study'] = path.relative_to(ROOT).as_posix()
        plan['conditions'] = []
        eligible = conditions(base)
        if 'conditions' in config:
            requested = set(config['conditions'])
            assert requested <= {c['id'] for c in eligible}, requested
            eligible = [c for c in eligible if c['id'] in requested]
        variables = config['variables']
        for values in product(*variables.values()):
            parameters = dict(zip(variables, values))
            label = '_'.join(f'{key}_{value}' for key, value in parameters.items()).replace('.', 'p')
            for condition in eligible:
                item = deepcopy(condition)
                item['id'] = identifier(label + '__' + condition['id'])
                item['study_parameters'] = parameters
                item['source_edits'] = [dict(edit, value=edit['value'].format(**parameters))
                                        for edit in config.get('edits', [])]
                item['topology'] = {key: parameters[variable]
                                    for key, variable in config.get('topology', {}).items()}
                plan['conditions'].append(item)
    else:
        raise ValueError('Expected flow.json or study.json')
    if 'measurement_file' in plan:
        plan['measurement'] = read_json(ROOT / plan.pop('measurement_file'))
    ids = [c['id'] for c in plan['conditions']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate condition IDs in ' + str(path))
    if selected:
        missing = set(selected) - set(ids)
        if missing:
            raise ValueError(f'Unknown conditions: {sorted(missing)}')
        plan['conditions'] = [c for c in plan['conditions'] if c['id'] in selected]
    if not plan['conditions']:
        raise ValueError('Plan contains no cases')
    return plan

"""Check saved Maestro settings and native point netlists against the flow."""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

from regression.common.project import read_json, write_json
from regression.common.units import numeric
from .plan import assignments, job_timeout_s


def same_value(expected, actual):
    if expected == actual:
        return True
    try:
        return math.isclose(numeric(expected.strip('()')), numeric(actual.strip('()')), rel_tol=1e-12, abs_tol=1e-30)
    except ValueError:
        return False


def verify_tb(tb, text):
    instances = {}
    top = re.sub(r'^subckt\b.*?^ends[^\n]*', '', text, flags=re.M | re.S)
    for line in re.sub(r'\\\r?\n', ' ', top).splitlines():
        match = re.fullmatch(r'(\w+)\s+\(([^)]*)\)\s+(\w+)\s*(.*)', line.strip())
        if match:
            name, nodes, model, params = match.groups()
            instances[name] = dict(nodes=nodes.split(), model=model, parameters=assignments(params))
    if set(instances) != {row['name'] for row in tb['instances']}:
        raise ValueError('Native TB instance set differs')
    for row in tb['instances']:
        actual = instances[row['name']]
        if (actual['nodes'], actual['model']) != (row['nodes'], row['model']):
            raise ValueError('Native TB connection/model differs: ' + row['name'])
        for key, value in row['parameters'].items():
            native = actual['parameters'].get(key, '')
            left, right = ([value], [native]) if key != 'wave' else (value.strip('[] ').split(), native.strip('[] ').split())
            if len(left) != len(right) or not all(same_value(a, b) for a, b in zip(left, right)):
                raise ValueError('Native TB parameter differs: ' + row['name'] + '.' + key)


def verify_point(plan, test, corner, text, remote, library):
    verify_tb(plan['tb'], text)
    flattened = re.sub(r'\\\r?\n', ' ', text)
    option = re.search(r'\btemp=([^\s]+)', flattened)
    temperature = option[1] if option else ''
    if temperature == 'temperature':
        variable = re.search(r'\btemperature=([^\s]+)', flattened)
        temperature = variable[1] if variable else ''
    if not same_value(str(corner['temperature']), temperature):
        raise ValueError('Exported corner temperature differs')
    sections = re.findall(r'\bsection="?([\w]+)', flattened)
    if sections != corner['model_sections']:
        raise ValueError('Exported model sections differ')
    for file in ('saves.scs',):
        if f'include "{remote}/{test["name"]}/inputs/{file}"' not in text:
            raise ValueError('Missing fixed TB saves')
    for row in plan['tb']['instances']:
        if row['model'] not in ('vsource', 'capacitor'):
            binding = '// Library name: '+library+'\n// Cell name: '+row['model']+'\n// View name: schematic\nsubckt '+row['model']
            if binding not in text:
                raise ValueError('DUT schematic hierarchy was not netlisted: ' + row['model'])
    if 'definitions.scs' in text:
        raise ValueError('Staged circuit wrapper is still included')
    tran = re.search(r'^tran tran (.*)$', flattened, re.M)
    actual = assignments(tran[1]) if tran else {}
    for key, value in test['analysis'].items():
        if not same_value(str(value), actual.get(key, '')):
            raise ValueError('Native transient option differs: ' + key)
    if not re.search(r'^saveOptions options save=selected\b', flattened, re.M):
        raise ValueError('Save mode differs from fixed TB')


def verify(client, run):
    from virtuoso.oa.native import evaluate, q
    record = read_json(run/'setup.json')
    plan = record['plan']
    mae = client.maestro
    session = mae.open_session(record['library'], plan['cell'])
    reports = []
    try:
        for name in ('maestro.sdb', 'active.state'):
            result = client.download_file(record['library_path']+'/'+plan['cell']+'/maestro/'+name, run/name)
            if not result.ok:
                raise RuntimeError(str(result))
        active = ET.parse(run/'maestro.sdb').getroot().find('active')
        enabled = {node.text.strip(): node for node in active.findall('corners/corner')
                   if node.get('enabled', '1') != '0'}
        if set(enabled) != {c['name'] for c in plan['corners']}:
            raise ValueError('Saved corner set differs, including Nominal enable state')
        tests = {node.text.strip(): node for node in active.findall('tests/test')}
        if set(tests) != {t['name'] for t in plan['tests']}:
            raise ValueError('Saved test set differs')
        policy = evaluate(client, f'maeGetJobPolicy(?session {q(session)})')
        policy = dict(zip(policy[1::2], policy[2::2]))
        expected_policy = dict(name=record['library']+'_'+plan['cell'],
                               maxjobs=str(record['workers']),
                               runtimeout=str(job_timeout_s(plan)))
        if any(policy.get(k) != v for k, v in expected_policy.items()):
            raise ValueError('Saved job policy differs from the prepared resource budget')
        state = ET.parse(run/'active.state').getroot()
        for option, value in (('switchViewList', '("spectre" "schematic")'),
                              ('stopViewList', '("spectre")')):
            saved = [field.text for field in state.iter('field') if field.get('Name') == option]
            if saved != [value]*len(tests):
                raise ValueError('Saved hierarchy view selection differs: ' + option)
        for test in plan['tests']:
            name = test['name']
            binding = {node.text.strip(): node.findtext('value').strip()
                       for node in tests[name].findall('tooloptions/option')}
            if any(binding.get(k) != v for k,v in dict(lib=record['library'], cell=plan['cell'], view='schematic').items()):
                raise ValueError('Saved test design binding differs: ' + name)
            saved_variables = {node.text.strip(): node.findtext('value').strip().split(',')
                               for node in tests[name].findall('vars/var')}
            expected_variables = {k: list(map(str, v)) for k, v in test['variables'].items()}
            if saved_variables != expected_variables:
                raise ValueError('Saved test variable sweeps differ: ' + name)
            options = evaluate(client, f'''let((th) th=maeGetTestSession({q(name)} ?session {q(session)})
                list(asiGetHighPerformanceOptionVal(th 'uniMode)
                     asiGetHighPerformanceOptionVal(th 'spectreXPreset)
                     asiGetHighPerformanceOptionVal(th 'spectreXMtOption)
                     asiGetHighPerformanceOptionVal(th 'spectreXNumThreads)
                     asiGetKeepOptionVal(th 'save)))''')
            expected = ['Spectre X', plan['simulator']['precision']['preset'], 'Manual',
                        str(plan['simulator']['threads']), 'selected']
            if options != expected:
                raise ValueError(f'Saved simulator settings differ: {options}')
            for corner in plan['corners']:
                destination = record['remote']+'/verified/'+name+'/'+corner['name']
                mae.create_netlist_for_corner(name, corner['name'], destination, session=session)
                local = run/'netlists'/name/(corner['name']+'.scs')
                local.parent.mkdir(parents=True, exist_ok=True)
                result = client.download_file(destination+'/netlist/input.scs', local)
                if not result.ok:
                    raise RuntimeError(str(result))
                verify_point(plan, test, corner, local.read_text(encoding='utf-8'), record['remote'], record['library'])
                reports.append(dict(test=name, corner=corner['name'], pass_=True))
        report = dict(pass_=True, tests=len(tests), corners=len(enabled),
                      points=len(plan['points']), workers=record['workers'], native_netlists=reports)
        write_json(run/'verification.json', report)
        return report
    finally:
        mae.close_session(session)

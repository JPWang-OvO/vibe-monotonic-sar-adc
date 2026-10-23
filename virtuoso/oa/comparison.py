"""Compare native readback and Spectre text with explicit name/path mappings."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
import re


GENERATED_PROPERTIES = {
    'connectivityLastUpdated', 'lastSchematicExtraction', 'schGeometryLastUpdated',
    'schGeometryVersion', 'schXtrVersion', 'interfaceLastChanged',
}


def expand_signals(names):
    """Expand ordered scalar, comma-list and <msb:lsb> signal expressions."""
    result=[]
    for expression in names:
        for name in expression.split(','):
            bus=re.fullmatch(r'(.+)<(\d+):(\d+)>',name)
            if bus:
                first,last=int(bus[2]),int(bus[3]);step=1 if last>=first else -1
                result.extend(f'{bus[1]}<{bit}>' for bit in range(first,last+step,step))
            else:result.append(name)
    return result


def circuit_semantics(circuit, library_map):
    result=deepcopy(circuit)
    result['properties']=[p for p in result['properties']
        if p['name'] not in GENERATED_PROPERTIES and not p['name'].endswith('#')]
    for instance in result['instances']:
        instance['master'][0]=library_map.get(instance['master'][0],instance['master'][0])
    return result


def drawing_objects(drawing):
    """Resolve local figure indices before comparing unordered native objects."""
    def shape(index):
        obj=deepcopy(drawing['shapes'][index])
        if 'parent' in obj and obj['parent'][0]!='inst':
            obj['parent']=[obj['parent'][0],shape(obj['parent'][1])]
        return obj
    shapes=[shape(idx) for idx in range(len(drawing['shapes']))]
    pins=deepcopy(drawing['pins'])
    for pin in pins:
        if pin['figure_type']!='inst':
            pin['figure']=shapes[pin['figure']]
    encode=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False)
    return dict(instances=drawing['instances'],
                pins=Counter(map(encode,pins)),shapes=Counter(map(encode,shapes)))


def spectre_tokens(text, replacements=()):
    """Ignore comments/spacing; keep quoted strings and all executable tokens.

    Each replacement is an explicit whole library name or generated path prefix.
    No numerical, expression, terminal-order or instance-order normalization occurs.
    """
    for old,new in replacements:
        if '/' in old:
            text=text.replace(old,new)
        else:
            text=re.sub(r'(?<![\w])'+re.escape(old)+r'(?![\w])',lambda _:new,text)
    pattern=r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/|\\\r?\n|[^\s"/(){}=,+*]+|[^\s]'
    tokens=[]
    for match in re.finditer(pattern,text):
        token=match[0]
        if token.startswith(('//','/*')) or token in ('\\\n','\\\r\n'):
            continue
        tokens.append(token)
    return tokens


def first_difference(expected,actual):
    for idx,(left,right) in enumerate(zip(expected,actual)):
        if left!=right:
            return dict(index=idx,expected=expected[max(0,idx-4):idx+5],
                        actual=actual[max(0,idx-4):idx+5])
    if len(expected)!=len(actual):
        return dict(index=min(len(expected),len(actual)),expected_length=len(expected),actual_length=len(actual))
    return None


def design_equivalent(expected, actual):
    """Compare connectivity and declared design parameters against native output."""
    from regression.common.units import numeric

    def parameters(tokens):
        result = {}
        starts = [i for i in range(len(tokens)-1) if tokens[i+1] == '=']
        for index, start in enumerate(starts):
            end = starts[index+1] if index+1 < len(starts) else len(tokens)
            result[tokens[start]] = ''.join(tokens[start+2:end])
        return result

    if expected['parameters'] != actual['parameters'] or expected['statements'].keys() != actual['statements'].keys():
        return False
    for name, left in expected['statements'].items():
        right = actual['statements'][name]
        split = left.index(')') + 2
        if left[:split] != right[:split]:
            return False
        native = parameters(right[split:])
        for key, value in parameters(left[split:]).items():
            if key not in native:
                return False
            if value == native[key]:
                continue
            try:
                equal = numeric(value) == numeric(native[key])
            except ValueError:
                equal = False
            if not equal:
                return False
    return True


def spectre_document(text, replacements=()):
    """Align named declarations; preserve every instance's ordered token list."""
    text=re.sub(r'\\\r?\n',' ',text)
    document={'subcircuits':{},'top':{'parameters':{},'statements':{},'directives':[]}}
    current=document['top']
    for line in text.splitlines():
        tokens=spectre_tokens(line,replacements)
        if not tokens:
            continue
        command=tokens[0]
        if command=='subckt':
            name=tokens[1]
            if name in document['subcircuits']:
                raise ValueError(f'Duplicate subcircuit: {name}')
            current={'ports':tokens[2:],'parameters':{},'statements':{},'directives':[]}
            document['subcircuits'][name]=current
        elif command=='ends':
            current['end']=tokens[1:]
            current=document['top']
        elif command=='parameters':
            index=1
            while index<len(tokens):
                name=tokens[index]
                if name in current['parameters']:
                    raise ValueError(f'Duplicate parameter: {name}')
                index+=1
                value=[]
                if index<len(tokens) and tokens[index]=='=':
                    index+=1
                    while index<len(tokens) and not (index+1<len(tokens) and tokens[index+1]=='=' and re.fullmatch(r'[A-Za-z_]\w*',tokens[index])):
                        value.append(tokens[index]);index+=1
                current['parameters'][name]=value
        elif command in ('simulator','global','include','ahdl_include'):
            current['directives'].append(tokens)
        else:
            if command in current['statements']:
                raise ValueError(f'Duplicate statement: {command}')
            current['statements'][command]=tokens[1:]
    return document

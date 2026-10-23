"""Read the frozen ADC hierarchy and its qualified native device properties."""
from pathlib import Path
import ast
from collections import defaultdict
import re

from regression.common.project import ROOT, read_json
from regression.common.units import numeric
from regression.common.tsmc18_enrichment import TAIL
from .comparison import spectre_document


def assignments(tokens):
    starts = [i for i in range(len(tokens)-1) if tokens[i+1] == '=']
    return {tokens[start]: ''.join(tokens[start+2:(starts[j+1] if j+1 < len(starts) else len(tokens))])
            for j, start in enumerate(starts)}


def clean_name(name):
    return name.replace('\\-', '-')


def cel(expression, parameters):
    for name in sorted(parameters, key=len, reverse=True):
        expression = re.sub(r'\b'+re.escape(name)+r'\b', lambda _: 'pPar("'+name+'")', expression)
    return expression


def hierarchy(batch_folder):
    folder = Path(batch_folder)
    batch = read_json(folder/'batch.json')
    case = batch['cases'][0]
    definitions = {}
    for source in case['sources']['sources']:
        if source == case['sources']['entry']:
            continue
        for name, data in spectre_document((folder/'cases'/case['id']/'inputs'/source).read_text())['subcircuits'].items():
            assert name not in definitions, name
            statements = []
            for instance, tokens in data['statements'].items():
                end = tokens.index(')')
                statements.append(dict(name=clean_name(instance), nodes=tokens[1:end],
                                       model=tokens[end+1], parameters=assignments(tokens[end+2:])))
            definitions[name] = dict(cell=name, ports=[p for p in data['ports'] if p not in ('(', ')')],
                                     parameters={k: ''.join(v) for k, v in data['parameters'].items()},
                                     instances=statements, staged_source=source)
    # Parent references determine connections; the installed standard-cell master
    # remains in its original library.
    for data in definitions.values():
        for inst in data['instances']:
            model = inst['model']
            ports = definitions[model]['ports'] if model in definitions else (
                ['PLUS', 'MINUS'] if model == 'capacitor' else ['D', 'G', 'S', 'B'])
            assert len(inst['nodes']) == len(ports), (data['cell'], inst)
            inst['connections'] = dict(zip(ports, inst['nodes']))
    return definitions, folder/'cases'/case['id']/'enrichment'


def source_folders():
    return {read_json(p)['cell']: p.parent for p in (ROOT/'library').rglob('cell.json')}


class QualifiedProperties:
    """Reuse properties computed by the accepted batch's PDK callbacks.

    Geometry is checked before reuse. Native standard-cell-derived devices keep
    their explicitly supplied parasitics. No PDK callback or source mutation is
    performed by this reader.
    """
    def __init__(self, enrichment):
        self.masters = {v: k for k, v in read_json(ROOT/'config/processes/tsmc18_callbacks.json')['models'].items()}
        self.by_geometry = {}
        for inst in read_json(Path(enrichment)/'prototype_readback.json')['instances']:
            p = inst['params']
            key = self.key(p['model'], p['wf'], p['l'], p['fingers'])
            tails = {k: p[k] for k in TAIL}
            if key in self.by_geometry:
                previous = self.by_geometry[key]
                assert all(numeric(previous[k]) == numeric(tails[k]) for k in TAIL), key
            self.by_geometry[key] = tails

    @staticmethod
    def key(model, width, length, fingers):
        return model, *(round(numeric(x), 18) for x in (width, length, fingers))

    def device(self, inst, parent_parameters):
        model, p = inst['model'], inst['parameters']
        if model == 'capacitor':
            return ['analogLib', 'cap', 'symbol'], {'c': cel(p['c'], parent_parameters)}
        if model not in self.masters:
            return ['standard_cells' if model == 'INVD1BWP7T' else 'MONOTONIC_SAR', model, 'symbol'], {
                k: cel(v, parent_parameters) for k, v in p.items()}
        key = self.key(model, p['w'], p['l'], p.get('nf', '1'))
        tails = {k: p[k] for k in TAIL} if all(k in p for k in TAIL) else self.by_geometry[key]
        params = dict(tails)
        params.update(model=model, wf=p['w'], w=format(numeric(p['w'])/numeric(p.get('nf', '1')), '.16g'),
                      l=p['l'], fingers=p.get('nf', '1'), simM=cel(p.get('m', '1'), parent_parameters))
        return ['tsmc18', self.masters[model], 'symbol'], params


def prepare_source(batch_folder):
    definitions, enrichment = hierarchy(batch_folder)
    qualified = QualifiedProperties(enrichment)
    for name, data in definitions.items():
        for inst in data['instances']:
            inst['master'], inst['oa_parameters'] = qualified.device(inst, data['parameters'])
    return definitions


def expression_value(expression, scope):
    """Evaluate the arithmetic grammar actually used by this ADC hierarchy."""
    engineering = r'(?<![\w.])((?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)([afpnumkMG])\b'
    expression = re.sub(engineering, lambda m: repr(float(numeric(m[0]))), expression)
    def visit(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name):
            return scope[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return (-1 if isinstance(node.op, ast.USub) else 1)*visit(node.operand)
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return a+b
            if isinstance(node.op, ast.Sub): return a-b
            if isinstance(node.op, ast.Mult): return a*b
            if isinstance(node.op, ast.Div): return a/b
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'max':
            return max(visit(n) for n in node.args)
        raise ValueError('Unsupported ADC parameter expression: '+expression)
    return float(visit(ast.parse(expression, mode='eval').body))


def flatten(definitions, top='MONOTONIC_SAR', qualified=None):
    """Canonical primitive connectivity and effective parameters.

    Parallel driver arrays are expanded electrically and summed by multiplicity;
    all other hierarchy paths and internal node names remain explicit.
    """
    devices = defaultdict(float)
    def descend(cell, nets, path, passed, multiplicity=1):
        data = definitions[cell]
        scope = {}
        for key, expr in data['parameters'].items():
            scope[key] = passed[key] if key in passed else expression_value(expr, scope)
        assert set(passed) <= set(scope), (cell, passed, scope)
        def node(name):
            return nets[name] if name in nets else (path+'.'+name if path else name)
        for inst in data['instances']:
            model = inst['model']
            name = clean_name(inst['name']).replace('\\<', '<').replace('\\>', '>')
            # Native netlisting expands I_out<9:0> into I_out<9> ... I_out<0>.
            # These members retain the source I_out9 ... I_out0 hierarchy names.
            name = re.sub(r'<(\d+)>$', r'\1', name)
            copies = 1
            array = re.fullmatch(r'(.*)<(\d+):(\d+)>', name)
            if array:
                name = array[1]
                copies = abs(int(array[2])-int(array[3]))+1
                assert model in ('SAR_DRIVE', 'SAR_DAC_DRIVE'), 'Only stateless parallel driver arrays are folded'
            connected = [node(n) for n in inst['nodes']]
            values = {k: expression_value(v, scope) for k, v in inst['parameters'].items()}
            if model in definitions:
                assert len(connected) == len(definitions[model]['ports'])
                descend(model, dict(zip(definitions[model]['ports'], connected)),
                        path+'.'+name if path else name, values, multiplicity*copies)
            else:
                count = values.pop('m', values.pop('multi', 1))*multiplicity*copies
                if model == 'capacitor':
                    values = {'c': values['c']}
                else:
                    values.setdefault('nf', 1)
                    if qualified is not None and not all(k in values for k in TAIL):
                        tails = qualified.by_geometry[qualified.key(model, values['w'], values['l'], values['nf'])]
                        values.update({k: float(numeric(v)) for k, v in tails.items()})
                    values = {k: values[k] for k in ('w', 'l', 'nf', *TAIL)}
                key = model, tuple(connected), tuple(sorted((k, format(v, '.11g')) for k, v in values.items()))
                devices[key] += count
    descend(top, {p:p for p in definitions[top]['ports']}, '', {})
    return dict(devices)

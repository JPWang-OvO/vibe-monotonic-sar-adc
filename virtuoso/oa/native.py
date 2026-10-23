"""Read native circuit semantics and drawings through the shared Bridge."""
from __future__ import annotations

import json
from pathlib import Path

from virtuoso_bridge.virtuoso.skill_output import parse_sexpr


def q(value):
    return json.dumps(value, ensure_ascii=False)


def port_order(circuit):
    """Use an explicit schematic portOrder; otherwise the saved terminal order."""
    orders=[p['value']['skill'] for p in circuit['properties'] if p['name']=='portOrder']
    terms=[t['name'] for t in circuit['terminals']]
    order=parse_sexpr(orders[0]) if orders else terms
    if len(order)!=len(terms) or set(order)!=set(terms):
        raise ValueError('portOrder differs from the schematic interface')
    return order


def execute(client, code, *, timeout=120):
    result = client.execute_skill(f'progn({code})', timeout=timeout)
    if not result.ok:
        raise RuntimeError(str(result))
    return result.output


def evaluate(client, code, *, timeout=120):
    return parse_sexpr(execute(client, code, timeout=timeout))


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def number_tree(value):
    if isinstance(value, list):
        return [number_tree(v) for v in value]
    return None if value is None else float(value)


def properties(rows):
    values = []
    for name, kind, literal in rows or []:
        parsed = parse_sexpr(literal)
        if kind == 'int':
            parsed = int(parsed)
        elif kind == 'float':
            parsed = float(parsed)
        elif kind == 'boolean':
            parsed = bool(parsed)
        elif kind == 'hierProp':
            parsed = properties(parsed)
        elif kind not in ('string', 'time'):
            parsed = {'skill': literal}
        values.append(dict(name=name, type=kind, value=parsed))
    return sorted(values, key=lambda v: v['name'])


def load_reader(client):
    execute(client, Path(__file__).with_name('native_read.il').read_text(encoding='utf-8'))


def read_view(client, library, cell, view):
    raw = evaluate(client, f'p0ReadView({q(library)} {q(cell)} {q(view)})', timeout=300)
    view_type, props, instances, terminals, nets, shapes = raw
    circuit = dict(cell=cell, view=view, view_type=view_type, properties=properties(props),
                   instances=[], terminals=[], nets=[])
    drawing = dict(instances={}, pins=[], shapes=[])
    for name, lib, master, master_view, purpose, xy, orient, count, inst_props, terms in instances or []:
        circuit['instances'].append(dict(name=name, master=[lib, master, master_view],
            purpose=purpose, multiplicity=int(count or 1), properties=properties(inst_props),
            connections=dict(terms or [])))
        drawing['instances'][name] = dict(xy=number_tree(xy), orient=orient)
    for name, direction, net, term_props, pins in terminals or []:
        circuit['terminals'].append(dict(name=name, direction=direction, net=net,
                                        properties=properties(term_props)))
        for pin_name, kind, figure, pin_props in pins or []:
            drawing['pins'].append(dict(terminal=name, name=pin_name, figure_type=kind,
                figure=figure if kind == 'inst' else int(figure), properties=properties(pin_props)))
    for name, sig_type, global_, net_props in nets or []:
        circuit['nets'].append(dict(name=name, signal_type=sig_type, global_=bool(global_),
                                   properties=properties(net_props)))
    for row in shapes or []:
        kind,lpp,bbox,points,xy,text,attribute,height,justify,orient,font,label_type,net,parent,shape_props,path,arc,display = row
        shape = dict(type=kind, lpp=lpp, bbox=number_tree(bbox))
        for key,value in [('points',number_tree(points)),('xy',number_tree(xy)),('text',text),
                          ('attribute',attribute),('height',number_tree(height)),('justify',justify),
                          ('orient',orient),('font',font),('label_type',label_type),('net',net)]:
            if value is not None:
                shape[key] = value
        if parent:
            shape['parent'] = [parent[0], parent[1] if parent[0]=='inst' else int(parent[1])]
        if shape_props:
            shape['properties'] = properties(shape_props)
        if path:
            shape.update(width=float(path[0]), style=path[1])
        if arc:
            shape.update(ellipse_bbox=number_tree(arc[0]), angles=number_tree(arc[1:]))
        if display:
            shape['display'] = display
        drawing['shapes'].append(shape)
    circuit['instances'].sort(key=lambda i: i['name'])
    circuit['terminals'].sort(key=lambda t: t['name'])
    circuit['nets'].sort(key=lambda n: n['name'])
    return circuit, drawing

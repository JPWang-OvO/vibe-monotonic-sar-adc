"""Rebuild native OA views from the maintained reference sources."""
from __future__ import annotations

import argparse
import json
import re
import shlex
from math import floor, pi
from pathlib import Path

from .native import execute, q


def literal(value):
    if isinstance(value, dict):
        return "'" + value['skill']
    if value is None or value is False:
        return 'nil'
    if value is True:
        return 't'
    if isinstance(value, list):
        return 'list(' + ' '.join(map(literal, value)) + ')'
    return q(value)


def point(xy):
    return ':'.join(format(n, '.17g') for n in xy)


def points(xys):
    return 'list(' + ' '.join(map(point, xys)) + ')'


def props(obj, values, *, cellview=False, depth=0):
    generated = {'connectivityLastUpdated', 'lastSchematicExtraction',
                 'schGeometryLastUpdated', 'schGeometryVersion', 'schXtrVersion'}
    commands=[]
    for p in values:
        if cellview and (p['name'] in generated or p['name'].endswith('#')):
            continue
        if p['type']=='hierProp':
            hp=f'hp{depth}'
            commands.append(f'let(({hp}) {hp}=dbCreateHierProp({obj} {q(p["name"])}) {props(hp,p["value"],depth=depth+1)})')
        else:
            commands.append(f'dbReplaceProp({obj} {q(p["name"])} {q(p["type"])} {literal(p["value"])})')
    return '\n'.join(commands)


def graphic(s):
    kind, layer = s['type'], literal(s['lpp'])
    if kind == 'label':
        return (f'dbCreateLabel(cv {layer} {point(s["xy"])} {q(s["text"])} '
                f'{q(s["justify"])} {q(s["orient"])} {q(s["font"])} {s["height"]})')
    if kind == 'path':
        style=' '+q(s['style']) if 'style' in s else ''
        return f'dbCreatePath(cv {layer} {points(s["points"])} {s["width"]}{style})'
    if kind == 'arc':
        (x0,y0),(x1,y1) = s['ellipse_bbox']
        xm,ym = (x0+x1)/2,(y0+y1)/2
        quadrants = [[[xm,ym],[x1,y1]], [[x0,ym],[xm,y1]],
                     [[x0,y0],[xm,ym]], [[xm,y0],[x1,ym]]]
        start,stop = s['angles']
        return (f'let((a) a=dbCreateArc(cv {layer} {points(s["ellipse_bbox"])} '
                f'{points(quadrants[floor(start/(pi/2))%4])}) '
                f'a~>startAngle={start} a~>stopAngle={stop} a)')
    function = {'line':'dbCreateLine', 'rect':'dbCreateRect',
                'ellipse':'dbCreateEllipse','polygon':'dbCreatePolygon'}[kind]
    return f'{function}(cv {layer} {points(s.get("points",s["bbox"]))})'


def view_code(library, source_library, circuit, drawing):
    cell,view = circuit['cell'],circuit['view']
    code = [f'let((cv ns ts ins figs obj master pin) '
            f'when(ddGetObj({q(library)} {q(cell)} {q(view)}) error("Destination view already exists"))',
            'unwindProtect(progn(',
            f'cv=dbOpenCellViewByType({q(library)} {q(cell)} {q(view)} {q(circuit["view_type"])} "w")',
            'unless(cv error("Cannot create view"))',
            "ns=makeTable('nets nil) ts=makeTable('terms nil) ins=makeTable('instances nil) figs=makeTable('figures nil)",
            props('cv',circuit['properties'],cellview=True)]
    for n in circuit['nets']:
        name=q(n['name'])
        code += [f'ns[{name}]=dbMakeNet(cv {name})',f'ns[{name}]~>sigType={q(n["signal_type"])}',props(f'ns[{name}]',n['properties'])]
        if n['global_']:
            code.append(f'ns[{name}]~>isGlobal=t')
    for t in circuit['terminals']:
        name=q(t['name'])
        code += [f'ts[{name}]=dbCreateTerm(ns[{q(t["net"])}] {name} {q(t["direction"])})',props(f'ts[{name}]',t['properties'])]
    for i in circuit['instances']:
        lib,master,master_view=i['master']
        if lib==source_library:
            lib=library
        pos=drawing['instances'][i['name']]
        name=q(i['name'])
        code += [f'master=dbOpenCellViewByType({q(lib)} {q(master)} {q(master_view)} "" "r")',
                 'unless(master error("Missing instance master"))',
                 f'ins[{name}]=dbCreateInst(cv master {name} {point(pos["xy"])} {q(pos["orient"])})',
                 'dbClose(master)',f'unless(ins[{name}] error("Instance creation failed"))',
                 f'ins[{name}]~>purpose={q(i["purpose"])}',props(f'ins[{name}]',i['properties'])]
        for term,net in i['connections'].items():
            if net is not None:
                code.append(f'dbCreateConnByName(ns[{q(net)}] ins[{name}] {q(term)})')
    for idx,s in enumerate(drawing['shapes']):
        if s['type']=='textDisplay':
            owner_type,owner,assoc_type,assoc,*flags=s['display']
            if owner_type=='term' and assoc_type=='term' and flags[-1]=='attrAssocType':
                owner_expr=f'ts[{q(owner)}]'
                assoc_expr=f'ts[{q(assoc)}]'
            elif owner_type=='inst' and assoc_type=='label' and flags[-1]=='labelAssocType':
                owner_expr=f'ins[{q(owner)}]'
                assoc_expr='car(obj)'
                code += [f'obj=setof(s {owner_expr}~>master~>shapes s~>objType=="label" && s~>theLabel=={q(s["attribute"])})',
                         'unless(length(obj)==1 error("Ambiguous master label association"))']
            else:
                raise ValueError(f'Unsupported text display association: {s["display"]}')
            expr=(f'dbCreateTextDisplay({assoc_expr} {owner_expr} {literal(s["lpp"])} '
                  f't {point(s["xy"])} {q(s["justify"])} {q(s["orient"])} '
                  f'{q(s["font"])} {s["height"]} '+ ' '.join(literal(f) for f in flags[:-1])+f' {q(s["attribute"])} nil)')
        else:
            expr=graphic(s)
        code += [f'figs[{idx}]={expr}',f'unless(figs[{idx}] error("Shape creation failed: {idx}"))']
        if s['type']=='textDisplay' and s['display'][-1]=='labelAssocType':
            code.append(f'figs[{idx}]~>xy={point(s["xy"])}')
            # Creation composes the label orientation with its owning instance.
            # The saved readback contains the final cellview orientation.
            code.append(f'figs[{idx}]~>orient={q(s["orient"])}')
        if 'label_type' in s:
            code.append(f'figs[{idx}]~>labelType={q(s["label_type"])}')
        if s.get('net'):
            code.append(f'dbAddFigToNet(figs[{idx}] ns[{q(s["net"])}])')
        code.append(props(f'figs[{idx}]',s.get('properties',[])))
    for idx,s in enumerate(drawing['shapes']):
        if 'parent' in s:
            kind,key=s['parent']
            parent=f'ins[{q(key)}]' if kind=='inst' else f'figs[{key}]'
            code.append(f'figs[{idx}]~>parent={parent}')
    for pin in drawing['pins']:
        fig=f'ins[{q(pin["figure"])}]' if pin['figure_type']=='inst' else f'figs[{pin["figure"]}]'
        term=f'ts[{q(pin["terminal"])}]'
        code += [f'pin=dbCreatePin({term}~>net {fig} {q(pin["name"])} {term})',props('pin',pin['properties'])]
    code += ['dbSave(cv) t) when(cv dbClose(cv))))']
    return '\n'.join(code)


def write_and_load(client, code, local, remote):
    local=Path(local)
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(code,encoding='utf-8',newline='\n')
    result=client.upload_file(local,remote)
    if not result.ok:
        raise RuntimeError(str(result))
    execute(client,f'load({q(remote)})',timeout=300)

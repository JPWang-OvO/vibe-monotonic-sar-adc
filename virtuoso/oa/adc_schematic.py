"""Functional schematic placement and terminal-based routing for reviewed OA views."""
from collections import defaultdict
from copy import deepcopy
import re

from .geometry import anchors, transform, intersect, segments, four_way
from .geometry import instance, wire, label, pin
from .adc_drawing import direction
from .comparison import expand_signals
from .native import q
from .replay import props
from .libraries import installed_library


def symbol_anchors(drawing):
    """Use captured native terminal geometry, including manually moved pins."""
    xy={p['terminal']:tuple((a+b)/2 for a,b in zip(drawing['shapes'][p['figure']]['bbox'][0],
                                                  drawing['shapes'][p['figure']]['bbox'][1]))
        for p in drawing['pins']}
    xs=[p[0] for p in xy.values()];ys=[p[1] for p in xy.values()]
    result={}
    for name,(x,y) in xy.items():
        choices=[(abs(x-min(xs)),(-1,0)),(abs(x-max(xs)),(1,0)),
                 (abs(y-min(ys)),(0,-1)),(abs(y-max(ys)),(0,1))]
        delta = (0,1) if name == 'VDD' else (0,-1) if name == 'VSS' else min(choices,key=lambda z:z[0])[1]
        result[name]=((x,y),delta)
    return result


def on_segment(p,a,b):
    return min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])


def connected(a,b,edges):
    todo={i for i,(u,v) in enumerate(edges) if on_segment(a,u,v)}
    targets={i for i,(u,v) in enumerate(edges) if on_segment(b,u,v)};seen=set()
    while todo:
        i=todo.pop()
        if i in targets:return True
        if i in seen:continue
        seen.add(i)
        todo.update(j for j,e in enumerate(edges) if j not in seen and intersect(*edges[i],*e))
    return False


def prune(lines, terminals):
    """Remove unused branch ends and collinear vertices in a scalar net tree."""
    vertices=set(terminals)
    for a,b in lines:vertices.update((a,b))
    for i,(a,b) in enumerate(lines):
        for c,d in lines[i+1:]:
            if not intersect(a,b,c,d):continue
            if a[0]==b[0] and c[1]==d[1]:vertices.add((a[0],c[1]))
            elif a[1]==b[1] and c[0]==d[0]:vertices.add((c[0],a[1]))
    graph=defaultdict(set)
    for a,b in lines:
        ps=sorted(p for p in vertices if on_segment(p,a,b))
        for u,v in zip(ps,ps[1:]):graph[u].add(v);graph[v].add(u)
    seen=set();components=[]
    for p in list(graph):
        if p in seen:continue
        todo=[p];group=set()
        while todo:
            u=todo.pop()
            if u in group:continue
            group.add(u);todo.extend(graph[u]-group)
        seen.update(group)
        roots={u:u for u in group}
        def root(u):
            while roots[u]!=u:u=roots[u]
            return u
        edges=sorted((abs(u[0]-v[0])+abs(u[1]-v[1]),u,v)
                     for u in group for v in graph[u] if u<v)
        for _,u,v in edges:
            if root(u)==root(v):graph[u].remove(v);graph[v].remove(u)
            else:roots[root(v)]=root(u)
        if len(group & set(terminals))>1:
            todo=[u for u in group if len(graph[u])==1 and u not in terminals]
            while todo:
                u=todo.pop()
                if len(graph[u])!=1 or u in terminals:continue
                v=next(iter(graph[u]));graph[v].remove(u);graph[u].clear()
                if len(graph[v])==1 and v not in terminals:todo.append(v)
        # Collapse degree-two collinear vertices into single straight wires.
        for u in sorted(group):
            if len(graph[u])!=2 or u in terminals:continue
            a,b=sorted(graph[u])
            if a[0]==u[0]==b[0] or a[1]==u[1]==b[1]:
                graph[a].remove(u);graph[b].remove(u);graph[a].add(b);graph[b].add(a);graph[u].clear()
        edges=[(u,v) for u in sorted(group) for v in sorted(graph[u]) if u<v]
        if edges:components.append(edges)
    return components


def schematic(data, master_drawings, *, layout, library_map=None):
    """Route the selected view from its current native semantic/drawing base."""
    pos,notes=deepcopy(layout)
    assert set(pos)=={i['name'] for i in data['instances']},data['cell']
    commands=[]; stubs=defaultdict(list); lines=[]; bodies=[];uses=defaultdict(int)
    def create_wire(path):
        # Geometry and labels are planned together. Automatic routing can move a
        # segment away from its label and create an unnamed, disconnected net.
        return wire(path,route_style='draw',route_mode='direct')
    for inst in data['instances']:
        name=inst['name'];p=pos[name];model=inst['model'];x,y=p['xy']
        values=[dict(name=k,type='string',value=v) for k,v in inst['oa_parameters'].items()]
        lib,cell,view=inst['master']
        commands.append('let((obj) obj='+instance(installed_library(lib,library_map),cell,view,name,x,y,p['orient'])+' '+props('obj',values)+')')
        if model in master_drawings:
            pinmap=symbol_anchors(master_drawings[model])
            coords=[a for a,d in pinmap.values()]
            box=[(min(a[0] for a in coords)+.0625,min(a[1] for a in coords)+.0625),
                 (max(a[0] for a in coords)-.0625,max(a[1] for a in coords)-.0625)]
        else:
            pinmap=anchors(inst)
            box=[(-.0625,-.15625),(.3125,.15625)] if model.startswith(('nch','pch')) else [(-.125,-.3125),(.125,-.0625)]
        corners=[transform((a,b),p) for a in [box[0][0],box[1][0]] for b in [box[0][1],box[1][1]]]
        bodies.append((min(a[0] for a in corners),min(a[1] for a in corners),max(a[0] for a in corners),max(a[1] for a in corners)))
        for term,(local,delta) in pinmap.items():
            a=transform(local,p);length=.25
            b=transform((local[0]+delta[0]*length,local[1]+delta[1]*length),p)
            net=inst['connections'][term]
            stubs[net].append((a,b,name,term))
            lines.append((net,a,b))
            members=expand_signals([net]);array=re.fullmatch(r'.*<(\d+):(\d+)>',name)
            count=abs(int(array[1])-int(array[2]))+1 if array else 1
            for member in members:uses[member]+=1 if len(members)>1 else count
    for i,(net,a,b) in enumerate(lines):
        for other,c,d in lines[i+1:]:
            assert net==other or not intersect(a,b,c,d),(data['cell'],'terminal overlap',net,other,a,b,c,d)
    controls={'CP','Hold','CDN','SDN','Reset','Sample','SampleB','ClkC','Bias','Gate'}
    for net,items in stubs.items():
        if net in ('VDD','VSS'):continue
        roots=list(range(len(items)))
        def root(i):
            while roots[i]!=i:i=roots[i]
            return i
        candidates=sorted((abs(a[0]-b[0])+abs(a[1]-b[1]),i,j,a,b)
                          for i,(_,a,_,ta) in enumerate(items) for j,(_,b,_,tb) in enumerate(items)
                          if i<j and ta!='B' and tb!='B')
        for dist,i,j,a,b in candidates:
            if root(i)==root(j) or dist>8 or (net in controls and dist>2.5):continue
            if connected(a,b,[(u,v) for other,u,v in lines if other==net]):
                roots[root(j)]=root(i);continue
            paths=([[a,b]] if a[0]==b[0] or a[1]==b[1] else
                   [[a,(a[0],b[1]),b],[a,(b[0],a[1]),b]])
            # A centered trunk is useful between the two sides of a TG or latch.
            for x in sorted({(a[0]+b[0])/2,a[0]-.375,b[0]+.375}):paths.append([a,(x,a[1]),(x,b[1]),b])
            for y in sorted({(a[1]+b[1])/2,a[1]+.375,b[1]-.375}):paths.append([a,(a[0],y),(b[0],y),b])
            paths=[list(dict.fromkeys(path)) for path in paths]
            paths.sort(key=lambda path:sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in segments(path))+.5*(len(path)-2))
            for path in paths:
                if any(intersect(u,v,c,d) for u,v in segments(path) for other,c,d in lines if other!=net):continue
                if any(intersect(u,v,(r[0],r[1]),(r[2],r[3])) for u,v in segments(path) for r in bodies):continue
                if four_way([(c,d) for other,c,d in lines if other==net],path):continue
                lines.extend((net,u,v) for u,v in segments(path));roots[root(j)]=root(i);break
    # One ordered label per connected bus avoids stacked labels on short stages.
    for net,items in stubs.items():
        if net in ('VDD','VSS'):
            for a,b,_,term in items:
                commands.append(create_wire([a,b]));commands.append(wire_label(a,b,net,terminal=True,bulk=term=='B',gate=term=='G'))
        else:
            components=prune([(a,b) for other,a,b in lines if other==net],{a for a,b,_,_ in items})
            for edges in components:
                for a,b in edges:commands.append(create_wire([a,b]))
                attached=[(a,b,name,term) for a,b,name,term in items if any(on_segment(a,u,v) for u,v in edges)]
                if len(attached)==1 and len(edges)==1:
                    a,b,_,term=attached[0]
                    commands.append(wire_label(a,b,net,terminal=True,bulk=term=='B',gate=term=='G'))
                else:
                    a,b=max(edges,key=lambda e:(e[0][1]==e[1][1],abs(e[0][0]-e[1][0])+abs(e[0][1]-e[1][1])))
                    commands.append(wire_label(a,b,net))
    terminal_points=[a for items in stubs.values() for a,_,_,_ in items]
    xmin=min(p[0] for p in terminal_points)-1
    xmax=max(p[0] for p in terminal_points)+1
    ymin=min(p[1] for p in terminal_points)-.75
    ymax=max(p[1] for p in terminal_points)+.75
    supplies={'VDD','VSS','VREFP','VREFN'}
    banks={side:[p for p in data['ports'] if p not in supplies and
                 ('right' if direction(data['cell'],p)=='output' else 'left')==side] for side in ('left','right')}
    for port in data['ports']:
        side='right' if direction(data['cell'],port)=='output' else 'left'
        if port in supplies:
            x=(xmin+xmax)/2+(-.5 if port.startswith('VREF') else .5)
            if not uses.get(port,0):x=xmin
            y=ymin if port in ('VSS','VREFN') else ymax
            end=(x+.25,y)
        else:
            x=xmin if side=='left' else xmax
            y=(ymin+ymax)/2+(len(banks[side])-1)*.1875-banks[side].index(port)*.375
            end=(x+.25,y) if side=='left' else (x-.25,y)
        commands.append(pin(port,x,y,'R0',direction=direction(data['cell'],port)))
        commands.append(create_wire([(x,y),end]))
        if not any(uses.get(v,0) for v in expand_signals([port])):
            commands.append(instance('basic','noConn','symbol','NC_'+port,*end,'R90' if end[0]>x else 'R270'))
    ports=expand_signals(data['ports'])
    unused_bus_members=[]
    for net,items in stubs.items():
        members=expand_signals([net])
        unused=[n for n in members if uses[n]==1 and n not in ports]
        if unused and len(unused)==len(members):
            a,b,_,_=items[0]
            name='NC_'+net.replace(',','_')
            width=len(expand_signals([net]))
            if width>1:name+=f'<{width-1}:0>'
            commands.append(instance('basic','noConn','symbol',name,*b,'R90' if a[1]==b[1] else 'R0'))
        elif unused:
            unused_bus_members.extend(unused)
    if unused_bus_members:
        net=','.join(dict.fromkeys(unused_bus_members));width=len(set(unused_bus_members))
        a=(xmax-.5,ymin-.5);b=(xmax-.25,ymin-.5)
        commands.append(create_wire([a,b]));commands.append(wire_label(a,b,net))
        commands.append(instance('basic','noConn','symbol',f'NC_unused<{width-1}:0>',*b,'R90'))
    commands.append('cv~>portOrder=list('+' '.join(q(n) for n in data['ports'])+')')
    notes.insert(0,(xmin,ymax+1,data['cell']))
    for x,y,text in notes:
        commands.append(f'schCreateNoteLabel(cv {x}:{y} {q(text)} "lowerLeft" "R0" "stick" 0.125 "normalLabel")')
    return commands,pos


def wire_label(a,b,net,*,terminal=False,bulk=False,gate=False):
    horizontal=a[1]==b[1]
    if not terminal:
        x,y=(a[0]+b[0])/2,(a[1]+b[1])/2
        return label(x if horizontal else x-.04375,y+.04375 if horizontal else y,
                     net,'lowerCenter','R0' if horizontal else 'R90',height=.0625)
    # Opposing TG gates need the middle of each stub to keep clock names apart.
    x,y=b if terminal and (horizontal or not gate) else ((a[0]+b[0])/2,(a[1]+b[1])/2)
    backwards=b[0]<a[0] if horizontal else b[1]<a[1]
    return label(x,y,net,'lowerRight' if backwards else 'lowerLeft',
                 'R0' if horizontal else 'R90',height=.05 if bulk else .0625)

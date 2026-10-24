"""Functional schematic placement and terminal-based routing for reviewed OA views."""
from collections import defaultdict
from copy import deepcopy
import re

from .adc_build import anchors, transform, intersect, segments, four_way
from .adc_build import instance, wire, label, pin
from .adc_drawing import direction
from .comparison import expand_signals
from .native import q
from .replay import props


REDRAW = {'SAR_ARM','SAR_FAST_SEQ','SAR_CAPTURE_LATCH','SAR_OUTPUT_FF',
          'SAR_DFFS','SAR_DFFR','SAR_CMP','SAR_BOOST_HI','SAR_BOOST'}
SIMPLIFY = {'SAR_SELECT','SAR_SAMPLE','SAR_PHASE','SAR_OUT','SAR_NAND2','SAR_DAC_DRIVE'}


def functional_placement(data, saved):
    """Keep unselected manual placement; arrange storage in signal-flow order."""
    cell=data['cell']; pos=deepcopy(saved); notes=[]
    def put(name,x,y,orient='R0'):
        pos[name]=dict(xy=[x,y],orient=orient)
    def pair(stem,x,y=0):
        put('Mp_'+stem,x,y+.875);put('Mn_'+stem,x,y-.875)
    def inv(stem,x,y=0):
        put(stem+'-M_u3',x,y+.875);put(stem+'-M_u2',x,y-.875)
    def tg(p,n,x,y=0,feedback=False):
        put(p,x,y+(.875 if feedback else .625),'R270' if feedback else 'R90')
        put(n,x,y-(.875 if feedback else .625),'R90' if feedback else 'R270')
    def note(x,y,text):notes.append((x,y,text))
    if cell=='SAR_CAPTURE_LATCH':
        tg('Mp_in','Mn_in',0);pair('qb',3);pair('q',6)
        tg('Mp_fb','Mn_fb',3,3,True);pair('h',-3)
        note(-.75,1.75,'D -> N -> QB -> Q')
        note(2.25,4.5,'Hold: feedback closed')
        note(-3.75,1.75,'Hold / HoldB')
    elif cell in ('SAR_OUTPUT_FF','SAR_FAST_SEQ'):
        pair('d',0);tg('Mp_mi','Mn_mi',3)
        if cell=='SAR_OUTPUT_FF':pair('md',6)
        else:
            put('Mp_ma',6,2.125);put('Mp_mb',6,.875)
            put('Mn_ma',6,-.875);put('Mn_mb',7.75,-.875)
        pair('mb' if cell=='SAR_OUTPUT_FF' else 'master_buf',9);tg('Mp_mf','Mn_mf',6,4.5,True)
        tg('Mp_si','Mn_si',12)
        if cell=='SAR_OUTPUT_FF':pair('q',15)
        else:
            put('Mp_qa',15,2.125);put('Mp_qb',15,.875)
            put('Mn_qa',15,-.875);put('Mn_qb',16.75,-.875)
        pair('sb',18);tg('Mp_sf','Mn_sf',15,4.5,True)
        if cell=='SAR_OUTPUT_FF':pair('cp',-3)
        note(3,6.5,'MASTER: CP=0');note(12,6.5,'SLAVE: CP=1')
        note(0,3.5,'D -> DB');note(18,3.5,'Q -> SB')
    elif cell in ('SAR_DFFR','SAR_ARM'):
        # Clocked input inverter, master reset feedback, slave TG/NAND.
        for name,x,y in [('MI7',0,2.125),('MI6',0,.875),('MI5',0,-.875),('MI4',0,-2.125)]:put(name,x,y)
        inv('MI13',3)
        for name,x,y in [('MI43',.75,7.125),('MI44',2.5,7.125),('MI45',.75,5.875),
                         ('MI47',.75,4.125),('MI48',.75,2.875),('MI49',.75,1.625)]:
            put(name,x+4.5,y)
        tg('MI16','MI15',9,feedback=True)
        for name,x,y in [('MI21-M_u1',12,.875),('MI21-M_u2',13.75,.875),
                         ('MI21-M_u3',12,-.875),('MI21-M_u4',12,-2.125)]:put(name,x,y)
        inv('MI27',16)
        inv('MI14',13,5);tg('MI17','MI18',9,5)
        put('MI14-M_u3',13,5.875,'MY');put('MI14-M_u2',13,4.125,'MY')
        inv('MI31',0,-4.5);inv('MI32',3,-4.5)
        for name,x,y in [('C_storage',1.75,0),('C_stack',1.75,-1.5),
                         ('C_slave',10.5,0),('C_pstack',1.75,1.5)]:put(name,x,y)
        note(-.75,9,'MASTER: clocked input + reset feedback')
        note(8.25,9,'SLAVE: transfer + reset NAND + Q')
        note(-.75,-2.5,'CLOCK: CP -> CPB -> CP')
    elif cell=='SAR_DFFS':
        for name,y in [('MI28',2.125),('MI26',.875),('MI21',-.875),('MI19',-2.125)]:put(name,0,y)
        for name,x,y in [('MI32-M_u1',3,.875),('MI32-M_u2',4.75,.875),
                         ('MI32-M_u3',3,-.875),('MI32-M_u4',3,-2.125),
                         ('MI35',3,7.125),('MI34',3,5.875),('MI23',3,4.125),('MI24',3,2.875)]:put(name,x,y)
        tg('MI30','MI20',7,feedback=True);inv('MI25',10);inv('MI60',14)
        for name,x,y in [('MI31-M_u1',11,5.875),('MI31-M_u2',12.75,5.875),
                         ('MI31-M_u3',11,4.125),('MI31-M_u4',11,2.875)]:put(name,x,y)
        tg('MI33','MI22',7,5)
        inv('MI55',0,-4.5);inv('MI40',3,-4.5)
        for name,x,y in [('C_storage',1.75,0),('C_stack',4.75,6.5),('C_pstack',1.75,1.5)]:put(name,x,y)
        note(-.75,9,'MASTER: input + set NAND + feedback')
        note(6.25,9,'SLAVE: transfer + Q + set feedback')
        note(-.75,-2.5,'CLOCK: CP -> CPB -> CP')
    elif cell=='SAR_CMP':
        put('Mp_bias',3,5.75);put('Mp_clock',3,4.5)
        put('Mp_input_p',0,3);put('Mp_input_n',6.5,3,'MY')
        put('Mn_latch_p',.5,.5,'MY');put('Mn_latch_n',6,.5)
        put('Mn_reset_p',-2,.5);put('Mn_reset_n',8.5,.5,'MY')
        for name,x in [('I_out<1:0>',0),('I_out1<1:0>',3.75),('I_out2<1:0>',7.5)]:put(name,x,-2)
        for name,x in [('I_valid',0),('I_vb0',3.75),('I_vb1',7.5)]:put(name,x,-4)
        note(-2,7,'PMOS input pair / regenerative latch / reset')
        note(-2,-1,'Differential outputs');note(-2,-3,'Valid detection')
    elif cell in ('SAR_BOOST','SAR_BOOST_HI'):
        put('C_boot',4,1.1875)
        put('Mp_precharge',4,4);put('Mp_transfer',7,3,'R90')
        put('Mp_start',0,1.875);put('Mn_start',0,.125)
        put('Mn_trackq',2,.125)
        put('Mp_bottom' if cell.endswith('_HI') else 'Mn_bottom',3,-1.5,'R90' if cell.endswith('_HI') else 'R270')
        put('Mn_reset_bottom',6,-1.5);put('Mn_reset_gate',9,-1.5)
        note(-.75,5.5,'START / Q');note(3.25,5.5,'PRECHARGE / Cboot');note(7,5.5,'TRANSFER / Gate')
        note(3.25,-3,'Vin tracking');note(7,-3,'SampleB reset')
    elif cell=='SAR_SAMPLE':
        put('Mn_sample',5.625,0,'R270');put('Mp_junction',8,0,'R270')
    assert set(pos)=={i['name'] for i in data['instances']},(cell,set(pos)^{i['name'] for i in data['instances']})
    return pos,[n for n in notes if n[2]]


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
        result[name]=((x,y),min(choices,key=lambda z:z[0])[1])
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


def storage_paths(cell):
    if cell=='SAR_SAMPLE':
        return [('Gate',[(5.625,3.25),(5.625,.375)]),
                ('Top',[(5.8125,-.25),(7.8125,-.25)])]
    if cell in ('SAR_BOOST','SAR_BOOST_HI'):
        return [('Ct',[(4,1.1875),(4,3.25),(6.4375,3.25)]),
                ('Cb',[(4,.8125),(4,-.4375),(3.5625,-.4375),(3.5625,-1.25 if cell.endswith('_HI') else -1.75)]),
                ('Gate',[(7.5625,3.25),(9.25,3.25),(9.25,-1.3125)])]
    if cell=='SAR_CMP':
        return [('Xp',[(.25,.6875),(.25,2.8125)]),
                ('Xn',[(6.25,.6875),(6.25,2.8125)]),
                ('Xp',[(.25,1.5),(5.625,1.5),(5.625,.5)]),
                ('Xn',[(6.25,2),(.875,2),(.875,.5)]),
                ('Xp',[(-1.75,.6875),(.25,.6875)]),
                ('Xn',[(6.25,.6875),(8.25,.6875)])]
    if cell=='SAR_CAPTURE_LATCH':
        return [('N',[(.5625,0),(2.4375,0),(2.4375,3)]),
                ('Q',[(3.5625,3),(7.5,3),(7.5,0),(6.25,0)])]
    if cell in ('SAR_OUTPUT_FF','SAR_FAST_SEQ'):
        return [('DB',[(.25,0),(2.4375,0)]),
                ('M',[(3.5625,0),(5.25,0),(5.25,4.5),(5.4375,4.5)]),
                ('MB',[(6.5625,4.5),(10.5,4.5),(10.5,0),(9.25,0)]),
                ('MB',[(10.5,0),(11.4375,0)]),
                ('S',[(12.5625,0),(14.25,0),(14.25,4.5),(14.4375,4.5)]),
                ('SB',[(15.5625,4.5),(19.5,4.5),(19.5,0),(18.25,0)])]
    if cell in ('SAR_ARM','SAR_DFFR'):
        return [('net5',[(.25,0),(2.625,0)]),
                ('net5',[(5.5,5),(4.25,5),(4.25,1.75),(2.25,1.75),(2.25,0)]),
                ('net97',[(3.25,0),(8.4375,0)]),
                ('net100',[(9.5625,0),(11.625,0)]),
                ('net100',[(8.4375,5),(8.4375,2.5),(10.5,2.5),(10.5,0)]),
                ('net53',[(9.5625,5),(12.75,5)]),
                ('net109',[(12.25,0),(15.625,0)]),
                ('net109',[(14.75,0),(14.75,5),(13.375,5)]),
                ('net79',[(.25,-4.5),(2.625,-4.5)])]
    if cell=='SAR_DFFS':
        return [('net13',[(.25,0),(2.625,0)]),
                ('net13',[(3.25,5),(2.25,5),(2.25,0)]),
                ('net97',[(3.25,0),(6.4375,0)]),
                ('net20',[(7.5625,0),(9.625,0)]),
                ('net20',[(6.4375,5),(6.4375,2.5),(8.75,2.5),(8.75,0)]),
                ('net5',[(7.5625,5),(11.25,5)]),
                ('net79',[(10.25,0),(13.625,0)]),
                ('net11',[(.25,-4.5),(2.625,-4.5)])]
    return []


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


def schematic(data, base, master_drawings, symbols, *, layout=None, qualified=False, functional_routes=True):
    """Route the selected view from its current native semantic/drawing base."""
    initial={n:p for n,p in base['drawing']['instances'].items() if n in {i['name'] for i in data['instances']}}
    pos,notes=functional_placement(data,initial) if layout is None else deepcopy(layout)
    assert set(pos)=={i['name'] for i in data['instances']},data['cell']
    commands=[]; stubs=defaultdict(list); lines=[]; bodies=[];uses=defaultdict(int)
    def create_wire(path):
        return wire(path,route_style='draw',route_mode='direct') if data['cell']=='SAR_CMP' else wire(path)
    native={i['name']:i for i in base['circuit']['instances']}
    for inst in data['instances']:
        name=inst['name'];p=pos[name];model=inst['model'];x,y=p['xy']
        if qualified:
            values=[dict(name=k,type='string',value=v) for k,v in inst['oa_parameters'].items()]
        else:
            old=native.get(name)
            if old is None:
                stem=re.sub(r'_[pn]$','',name);old=native[stem+'<1:0>']
            values=old['properties']
        commands.append('let((obj) obj='+instance(*inst['master'],name,x,y,p['orient'])+' '+props('obj',values)+')')
        if model in master_drawings:
            pinmap=symbol_anchors(master_drawings[model])
            coords=[a for a,d in pinmap.values()]
            box=[(min(a[0] for a in coords)+.0625,min(a[1] for a in coords)+.0625),
                 (max(a[0] for a in coords)-.0625,max(a[1] for a in coords)-.0625)]
        else:
            pinmap=anchors(inst,symbols)
            box=[(-.0625,-.15625),(.3125,.15625)] if model.startswith(('nch','pch')) else [(-.125,-.3125),(.125,-.0625)]
        corners=[transform((a,b),p) for a in [box[0][0],box[1][0]] for b in [box[0][1],box[1][1]]]
        bodies.append((min(a[0] for a in corners),min(a[1] for a in corners),max(a[0] for a in corners),max(a[1] for a in corners)))
        for term,(local,delta) in pinmap.items():
            a=transform(local,p);length=.375
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
    for net,path in (storage_paths(data['cell']) if functional_routes else []):
        for a,b in segments(path):
            def crossover(other,c,d):
                if data['cell']!='SAR_CMP' or {net,other}!={'Xp','Xn'}:return False
                if a[0]==b[0] and c[1]==d[1]:return min(a[1],b[1])<c[1]<max(a[1],b[1]) and min(c[0],d[0])<a[0]<max(c[0],d[0])
                if a[1]==b[1] and c[0]==d[0]:return min(a[0],b[0])<c[0]<max(a[0],b[0]) and min(c[1],d[1])<a[1]<max(c[1],d[1])
                return False
            assert not any(other!=net and intersect(a,b,c,d) and not crossover(other,c,d) for other,c,d in lines),(data['cell'],'functional route crosses another net',net,a,b)
            assert not any(intersect(a,b,(r[0],r[1]),(r[2],r[3])) for r in bodies),(data['cell'],'functional route crosses a body',net,a,b)
            lines.append((net,a,b))
    controls={'CP','CPB','Hold','HoldB','CDN','SDN','Reset','Sample','SampleB','ClkC','Bias'}
    if data['cell'] in ('SAR_ARM','SAR_DFFR'):controls.update(('net79','net67'))
    elif data['cell']=='SAR_DFFS':controls.update(('net11','net9'))
    elif data['cell'] in ('SAR_BOOST','SAR_BOOST_HI'):controls.add('Gate')
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
    # Ordered array labels must be created at every terminal before joining buses.
    for net,items in stubs.items():
        vector=any('<' in name for _,_,name,_ in items)
        if vector:
            for a,b,name,term in items:
                commands.append(create_wire([a,b]));commands.append(wire_label(a,b,net,terminal=True,bulk=term=='B',gate=term=='G'))
            for other,a,b in lines:
                if other==net and not any((a,b)==(u,v) for u,v,_,_ in items):commands.append(create_wire([a,b]))
        elif net in ('VDD','VSS'):
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
    xmin=min(p['xy'][0] for p in pos.values())-3
    ymax=max(p['xy'][1] for p in pos.values())+.75
    for index,port in enumerate(data['ports']):
        x=xmin;y=min(ymax,2.5)-index*.5
        commands.append(pin(port,x,y,'R0',direction=direction(data['cell'],port)))
        commands.append(create_wire([(x,y),(x+.75,y)]));commands.append(label(x+.25,y,port,'lowerLeft','R0'))
        if not any(v in uses for v in expand_signals([port])):
            commands.append(instance('basic','noConn','symbol','NC_'+port,x+.75,y,'R90'))
    ports=expand_signals(data['ports'])
    for net,items in stubs.items():
        if all(uses[n]==1 and n not in ports for n in expand_signals([net])):
            a,b,_,_=items[0]
            name='NC_'+net.replace(',','_')
            width=len(expand_signals([net]))
            if width>1:name+=f'<{width-1}:0>'
            commands.append(instance('basic','noConn','symbol',name,*b,'R90' if a[1]==b[1] else 'R0'))
    commands.append('cv~>portOrder=list('+' '.join(q(n) for n in data['ports'])+')')
    notes.insert(0,(xmin,ymax+1,data['cell']))
    for x,y,text in notes:
        commands.append(f'schCreateNoteLabel(cv {x}:{y} {q(text)} "lowerLeft" "R0" "stick" 0.125 "normalLabel")')
    return commands,pos


def wire_label(a,b,net,*,terminal=False,bulk=False,gate=False):
    horizontal=a[1]==b[1]
    # Opposing TG gates need the middle of each stub to keep clock names apart.
    x,y=b if terminal and (horizontal or not gate) else ((a[0]+b[0])/2,(a[1]+b[1])/2)
    backwards=b[0]<a[0] if horizontal else b[1]<a[1]
    return label(x,y,net,'lowerRight' if backwards else 'lowerLeft',
                 'R0' if horizontal else 'R90',height=.05 if bulk else .0625)

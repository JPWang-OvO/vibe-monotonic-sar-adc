"""Native schematic geometry and bus connections."""
import re
from virtuoso_bridge.virtuoso.schematic import (
    schematic_create_inst_by_master_name as instance,
    schematic_create_wire as wire,
    schematic_create_wire_label as label,
    schematic_create_pin as pin,
)
from .comparison import expand_signals


def array_connections(inst):
    connections=inst['connections'];array=re.fullmatch(r'.*<(\d+):(\d+)>',inst['name'])
    if array:
        count=abs(int(array[1])-int(array[2]))+1
        connections={k:(v if len(expand_signals([v]))>1 else f'<*{count}>'+v)
                     for k,v in connections.items()}
    return connections


def transform(point, place):
    x,y=point
    if place['orient']=='MY': x=-x
    elif place['orient']=='MX': y=-y
    elif place['orient']=='R180': x,y=-x,-y
    elif place['orient']=='R90': x,y=-y,x
    elif place['orient']=='R270': x,y=y,-x
    elif place['orient']!='R0': raise ValueError(place['orient'])
    return (x+place['xy'][0],y+place['xy'][1])


def anchors(inst):
    model=inst['model']
    if model.startswith(('nch','pch')):
        dy=-.1875 if model.startswith('pch') else .1875
        return {'D':((.25,dy),(0,1 if dy>0 else -1)), 'G':((0,0),(-1,0)),
                'S':((.25,-dy),(0,-1 if dy>0 else 1)), 'B':((.25,0),(1,0))}
    if model=='capacitor': return {'PLUS':((0,0),(0,1)), 'MINUS':((0,-.375),(0,-1))}
    raise ValueError('Supply the native master drawing for '+model)



def segments(path):
    return list(zip(path,path[1:]))


def intersect(a,b,c,d):
    # Inclusive intersection: differently named wires must never even touch.
    return (max(min(a[0],b[0]),min(c[0],d[0])) <= min(max(a[0],b[0]),max(c[0],d[0])) and
            max(min(a[1],b[1]),min(c[1],d[1])) <= min(max(a[1],b[1]),max(c[1],d[1])))


def four_way(existing, path):
    """Keep same-net joins at T junctions so Check/Save has no crossover dots."""
    added=list(segments(path));all_lines=existing+added;points=set(path)
    for a,b in added:
        for c,d in existing:
            if not intersect(a,b,c,d):continue
            if a[0]==b[0] and c[1]==d[1]:points.add((a[0],c[1]))
            elif a[1]==b[1] and c[0]==d[0]:points.add((c[0],a[1]))
    for x,y in points:
        directions=set()
        for a,b in all_lines:
            if a[1]==b[1]==y and min(a[0],b[0])<=x<=max(a[0],b[0]):
                if min(a[0],b[0])<x:directions.add('left')
                if max(a[0],b[0])>x:directions.add('right')
            if a[0]==b[0]==x and min(a[1],b[1])<=y<=max(a[1],b[1]):
                if min(a[1],b[1])<y:directions.add('down')
                if max(a[1],b[1])>y:directions.add('up')
        if len(directions)==4:return True
    return False

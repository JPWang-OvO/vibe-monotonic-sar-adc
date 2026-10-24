"""Build editable ADC views only after the fixed 20-case electrical gate passes."""
import argparse
import re
from collections import defaultdict
from pathlib import Path

from regression.common.bridge_environment import load_bridge_environment
from regression.common.project import ROOT, artifact_root, read_json, write_json
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic import (
    schematic_create_inst_by_master_name as instance,
    schematic_create_wire as wire,
    schematic_create_wire_label as label,
    schematic_create_pin as pin,
)
from .adc_source import prepare_source, source_folders
from .adc_drawing import functional_symbol, symbol_commands, svg, direction
from .adc_layout import fold_drivers, placements
from .native import execute, evaluate, q, load_reader, read_view
from .replay import props, points
from .cells import check, capture
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
    elif place['orient']!='R0': raise ValueError(place['orient'])
    return (x+place['xy'][0],y+place['xy'][1])


def anchors(inst, symbols):
    model=inst['model']
    if model.startswith(('nch','pch')):
        dy=-.1875 if model.startswith('pch') else .1875
        return {'D':((.25,dy),(0,1 if dy>0 else -1)), 'G':((0,0),(-1,0)),
                'S':((.25,-dy),(0,-1 if dy>0 else 1)), 'B':((.25,0),(1,0))}
    if model=='capacitor': return {'PLUS':((0,0),(0,1)), 'MINUS':((0,-.375),(0,-1))}
    if model=='INVD1BWP7T':
        return {'I':((-.5,-.3125),(-1,0)), 'ZN':((-.0625,-.3125),(1,0)),
                'VDD':((-.3125,-.125),(0,1)), 'VSS':((-.3125,-.5),(0,-1))}
    delta={'left':(-1,0),'right':(1,0),'top':(0,1),'bottom':(0,-1)}
    return {n:(p['xy'],delta[p['side']]) for n,p in symbols[model].pins.items()}


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


def schematic(data, symbols):
    pos=placements(data); commands=[]; ends=defaultdict(list); labels=defaultdict(list); uses=defaultdict(int); lines=[]; bodies=[]
    for inst in data['instances']:
        name=inst['name']; p=pos[name]; x,y=p['xy']; model=inst['model']
        commands.append('let((obj) obj='+instance(*inst['master'],name,x,y,p['orient'])+' '+
                        props('obj',[dict(name=k,type='string',value=v) for k,v in inst['oa_parameters'].items()])+')')
        if model in symbols:
            pic=symbols[model]; bodies.append((x-pic.width/2,y-pic.height/2,x+pic.width/2,y+pic.height/2))
        elif model=='capacitor': bodies.append((x-.12,y-.33,x+.12,y-.04))
        elif model.startswith(('nch','pch')): bodies.append((x-.05,y-.15,x+.3,y+.15))
        else: bodies.append((x-.48,y-.45,x-.08,y-.15))
        for term,(local,delta) in anchors(inst,symbols).items():
            a=transform(local,p)
            b=transform((local[0]+delta[0]*.5,local[1]+delta[1]*.5),p)
            net=inst['connections'][term]
            array=re.fullmatch(r'.*<(\d+):(\d+)>',name)
            count=abs(int(array[1])-int(array[2]))+1 if array else 1
            members=expand_signals([net])
            for member in members:
                uses[member]+=1 if len(members)>1 else count
            commands.append(wire([a,b])); lines.append((net,a,b)); ends[net].append(b)
            mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2
            justify='lowerRight' if b[0]<a[0] or b[1]<a[1] else 'lowerLeft'
            rotation='R0' if a[1]==b[1] else 'R90'
            labels[net].append((len(commands),mx,my,justify,rotation))
            commands.append(label(mx,my,net,justify,rotation))
    for index,(net,a,b) in enumerate(lines):
        for other,c,d in lines[index+1:]:
            assert other==net or not intersect(a,b,c,d),(data['cell'],'Overlapping terminal stubs',net,other,a,b,c,d)
    # Join close members of each functional group wherever an unobstructed
    # orthogonal path exists. The remaining distributed nets retain their labels.
    for net,vertices in ends.items():
        edges=sorted((abs(a[0]-b[0])+abs(a[1]-b[1]),i,j,a,b)
                     for i,a in enumerate(vertices) for j,b in enumerate(vertices) if i<j)
        roots=list(range(len(vertices)))
        def root(i):
            while roots[i]!=i:i=roots[i]
            return i
        for distance,i,j,a,b in edges:
            if distance>5 or root(i)==root(j):continue
            candidates=([a,b],) if a[0]==b[0] or a[1]==b[1] else ([a,(a[0],b[1]),b],[a,(b[0],a[1]),b])
            for path in candidates:
                if any(intersect(u,v,c,d) for u,v in segments(path) for other,c,d in lines if other!=net):continue
                if four_way([(c,d) for other,c,d in lines if other==net],path):continue
                if any(intersect(u,v,(r[0],r[1]),(r[2],r[3])) for u,v in segments(path) for r in bodies):continue
                commands.append(wire(path));lines.extend((net,u,v) for u,v in segments(path))
                roots[root(j)]=root(i);break
        # Every array pin needs its explicit ordered label before routing.
        # Separate labels above/below short shared bus wires to avoid overlap.
        labelled=set()
        for index,(command_index,mx,my,justify,rotation) in enumerate(labels[net]):
            component=root(index)
            if component in labelled and len(expand_signals([net]))>1 and rotation=='R0':
                commands[command_index]=label(mx,my,net,justify.replace('lower','upper'),rotation)
            labelled.add(component)
    xmin=min(p['xy'][0] for p in pos.values())-3
    ymax=max(p['xy'][1] for p in pos.values())+3
    # Explicit external interface in grouped columns keeps every terminal visible.
    for index,port in enumerate(data['ports']):
        x=xmin-2*(index//16);y=ymax-.375*(index%16)
        commands.append(pin(port,x,y,'R0',direction=direction(data['cell'],port)))
        output_bus=direction(data['cell'],port)=='output' and len(expand_signals([port]))>1
        length=1.5 if output_bus else .75
        commands.append(wire([(x,y),(x+length,y)]))
        commands.append(label(x+(.75 if output_bus else .25),y,port,'lowerLeft','R0'))
        if not any(member in uses for member in expand_signals([port])):
            # Unused interface entries are retained to match the frozen netlist.
            commands.append(instance('basic','noConn','symbol','NC_'+port,x+length,y,'R90'))
    unused_bus=[]
    for net,count in uses.items():
        if count==1 and net not in expand_signals(data['ports']):
            if net in ends:
                x,y=ends[net][0]
            else:
                unused_bus.append(net)
                continue
            commands.append(instance('basic','noConn','symbol','NC_'+net,x,y,'R0'))
    if unused_bus:
        x=xmin+2;y=ymax
        commands.append(wire([(x-.75,y),(x,y)]))
        commands.append(label(x-.5,y,','.join(unused_bus),'lowerLeft','R0'))
        name='NC_unused'+(f'<{len(unused_bus)-1}:0>' if len(unused_bus)>1 else '')
        commands.append(instance('basic','noConn','symbol',name,x,y,'R90'))
    commands.append('cv~>portOrder=list('+' '.join(q(n) for n in data['ports'])+')')
    commands.append(f'schCreateNoteLabel(cv {xmin}:{ymax+.75} {q(data["cell"])} "lowerLeft" "R0" "stick" 0.125 "normalLabel")')
    return commands,pos


def cdf_commands(cell,parameters):
    if not parameters:return ''
    target=f'ddGetObj("MONOTONIC_SAR" {q(cell)})'
    out=[f'let((cdf) cdf=cdfGetBaseCellCDF({target}) unless(cdf cdf=cdfCreateBaseCellCDF({target}))']
    for name,value in parameters.items():
        out.append(f'unless(exists(p cdf~>parameters p~>name=={q(name)}) '
                   f'unless(cdfCreateParam(cdf ?name {q(name)} ?prompt {q(name)} ?type "string" ?defValue {q(value)} ?parseAsNumber "yes" ?parseAsCEL "yes") '
                   f'error("CDF parameter creation failed: %s" {q(name)})))')
    out.append('cdfSaveCDF(cdf))')
    return '\n'.join(out)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    definitions=prepare_source(args.batch)
    data={name:fold_drivers(value) for name,value in definitions.items() if name!='INVD1BWP7T'}
    symbols={name:functional_symbol(value) for name,value in data.items()}
    plans={name:schematic(value,symbols) for name,value in data.items()}
    if args.prepare_only:
        print('Prepared',len(plans),'cell plans without creating views or drawing artifacts');return
    gate=read_json(ROOT/'config/acceptance_results.json')
    assert gate['all_electrical_pass'] and gate['passed_cases']==20 and gate['dut_sources_equal']
    assert gate['cell_views']==read_json(args.batch/'batch.json')['cases'][0]['sources']['cell_views']
    env=read_json(ROOT/'config/environments/tsmc18.local.json')
    load_bridge_environment();client=VirtuosoClient.from_env(profile=env['profile'],log_to_ciw=False)
    run=artifact_root()/'oa_delivery';run.mkdir(exist_ok=True)
    remote=read_json(args.batch/'batch.json')['remote']
    if args.resume:
        mapping=read_json(run/'library_mapping.json')
        assert mapping['delivery_path']==env['oa_library_path']
        assert client.library.get('MONOTONIC_SAR').path==env['oa_library_path']
    else:
        visible=evaluate(client,'mapcar(lambda((l) list(l~>name l~>readPath)) ddGetLibList())')
        old_forced=evaluate(client,'ddGetForcedLib()')
        old_target=[path for name,path in visible if name=='MONOTONIC_SAR']
        if old_target:
            assert not evaluate(client,'ddGetObj("MONOTONIC_SAR")~>cells'),'Existing target contains cells; inspect before changing the active mapping'
        # Preserve every other mapping and the original empty directory.
        mapping=run/'cds.lib'
        mapping.write_text('\n'.join('DEFINE '+name+' '+path for name,path in visible if name!='MONOTONIC_SAR')+'\n',encoding='utf-8',newline='\n')
        write_json(run/'library_mapping.json',dict(previous_forced_file=old_forced,previous_target_paths=old_target,
                   active_cds_lib=remote+'/oa-cds.lib',delivery_path=env['oa_library_path']))
        response=client.upload_file(mapping,remote+'/oa-cds.lib');assert response.ok,str(response)
        assert evaluate(client,'ddSetForcedLib('+q(remote+'/oa-cds.lib')+')')
        assert evaluate(client,'ddUpdateLibList()')
        client.library.create('MONOTONIC_SAR',env['oa_library_path'],technology_library='tsmc18')
    folders=source_folders()
    for name,picture in symbols.items():
        exists=evaluate(client,'ddGetObj("MONOTONIC_SAR" '+q(name)+' "symbol")')
        if exists:
            assert args.resume,'Existing symbol '+name
        else:
            with client.symbol.create('MONOTONIC_SAR',name) as editor:
                for command in symbol_commands(picture):editor.add(command)
            execute(client,cdf_commands(name,data[name]['parameters']) or 't')
        folder=folders[name];(folder/'symbol').mkdir(exist_ok=True)
        (folder/'symbol/functional.svg').write_text(svg(picture),encoding='utf-8')
        print('symbol',name,flush=True)
    for name,(commands,positions) in plans.items():
        exists=evaluate(client,'ddGetObj("MONOTONIC_SAR" '+q(name)+' "schematic")')
        if exists:
            assert args.resume,'Existing schematic '+name
        else:
            with client.schematic.create('MONOTONIC_SAR',name,timeout=180) as editor:
                for command in commands:editor.add(command)
        check(client,'MONOTONIC_SAR',name)
        actual=client.schematic.read('MONOTONIC_SAR',name,include_positions=True,param_filters=None)
        observed={i['name']:i for i in actual['instances']}
        for expected in data[name]['instances']:
            connections=array_connections(expected)
            assert observed[expected['name']]['terms']==connections,(name,expected['name'],observed[expected['name']]['terms'],connections)
        assert set(actual['pins'])==set(data[name]['ports']),name
        write_json(run/(name+'_readback.json'),actual)
        write_json(folders[name]/'schematic/circuit.json',data[name])
        write_json(folders[name]/'schematic/placement.json',positions)
        print('schematic',name,flush=True)
    load_reader(client)
    for name in data:
        capture(client,'MONOTONIC_SAR',folders[name],run,remote)
        print('captured',name,flush=True)
    exported=client.schematic.export_netlist('MONOTONIC_SAR','MONOTONIC_SAR',run/'native_netlist',simulator='spectre',netlist_only=True)
    write_json(run/'export_result.json',{k:exported[k] for k in ('source_file','source_dir','output_dir','input_file')})
    print('Native export ready; electrical comparison and visual review remain required',flush=True)


if __name__=='__main__':main()

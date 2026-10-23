"""Native primitive MOS enrichment for this project's Spectre 19.1/TSMC18 PDK."""
import json,math,re,shlex,shutil,uuid,tarfile
from pathlib import Path
from .project import ROOT,read_json,write_json
from . import tsmc18_callbacks
from virtuoso_bridge.virtuoso.schematic.ops import schematic_create_inst_by_master_name as inst
from virtuoso_bridge.virtuoso.schematic.ops import schematic_create_pin as pin

TAIL=('sd','ad','as','pd','ps','nrd','nrs','sa','sb','sca','scb','scc')
PROTECTED=('w','l','nf','m')
SCALE={'':1,'m':1e-3,'u':1e-6,'n':1e-9,'p':1e-12,'f':1e-15,'a':1e-18,'k':1e3,'M':1e6,'G':1e9}

def parse_inst(text):
    rows={};current=None
    for line in text.splitlines():
        if line.startswith('Instance: '):
            name=line[10:].split(' of ')[0].strip();current={'parameters':{}};rows[name]=current
        elif line.startswith('Maximum and minimum'):
            current=None
        elif current is not None:
            if line.startswith('Model: '):current['model']=line[7:].strip()
            elif line.startswith('Primitive: '):current['primitive']=line[11:].strip()
            else:
                match=re.fullmatch(r'\s*(\w+)\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*)',line)
                if match:
                    key,number,unit=match.groups();value=float(number)
                    # Native output prints engineering prefix adjacent to SI unit.
                    if unit and len(unit)>1 and unit[0] in SCALE and unit[1:] in ('m','m^2','s','V','A','Hz','Ohm'):
                        value*=SCALE[unit[0]]
                    current['parameters'][key]=value
    return rows

def checked(r):
    if r.returncode:raise RuntimeError(r.stderr or r.stdout)
    return r.stdout+r.stderr

def inspect(client,remote_file,remote,out,env,arguments,alter_names=()):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'inspect.scs').write_text('simulator lang=spectre\ninclude '+json.dumps(remote_file)+'\nprintOpts options digits=17\nmsar_instances info what=inst where=file file="instances.txt"\nmsar_nodes info what=nodes where=file file="nodes.txt"\n',encoding='utf-8',newline='\n')
    (out/'inspect.mdl').write_text(''.join('run '+name+'\n' for name in alter_names)+'run msar_instances\nrun msar_nodes\n',encoding='utf-8',newline='\n')
    runner=client.ssh_runner
    checked(runner.run_command(shlex.join(['mkdir','-p',remote]),timeout=30))
    for name in ('inspect.scs','inspect.mdl'):
        checked(runner.upload(out/name,remote+'/'+name,timeout=30))
    cmd=[env['spectre'],'-64','inspect.scs','=mdlcontrol','inspect.mdl','+log','spectre.log',*arguments]
    r=runner.run_command('cd '+shlex.quote(remote)+' && '+shlex.join(cmd),timeout=180)
    (out/'command.log').write_text(r.stdout+r.stderr,encoding='utf-8')
    checked(r)
    # Large expanded standard-cell inventories are highly repetitive. Compress
    # the three native reports before transfer, without transferring raw PSF.
    checked(runner.run_command('cd '+shlex.quote(remote)+' && tar -czf inspection.tar.gz instances.txt nodes.txt spectre.log',timeout=30))
    checked(runner.download(remote+'/inspection.tar.gz',out/'inspection.tar.gz',timeout=30))
    with tarfile.open(out/'inspection.tar.gz') as archive:
        for member in archive:
            if not member.isfile() or member.name not in ('instances.txt','nodes.txt','spectre.log'):
                raise ValueError('Unexpected native report archive member')
            with archive.extractfile(member) as source,(out/member.name).open('wb') as target:
                shutil.copyfileobj(source,target)
    log=(out/'spectre.log').read_text()
    if 'spectre completes with 0 errors' not in log:raise ValueError('Native inspection did not complete cleanly')
    return parse_inst((out/'instances.txt').read_text())

def native_prototypes(client,prototypes,out,remote,config):
    token=uuid.uuid4().hex[:10]
    lib='MSAR_PDK_'+token.upper();cell='devices_'+token
    masters={v:k for k,v in config['models'].items()}
    client.library.create(lib,remote+'/oa_'+token,technology_library='tsmc18',timeout=60)
    try:
        with client.schematic.create(lib,cell,timeout=120) as sch:
            for i,(name,model,p) in enumerate(prototypes):
                create=inst('tsmc18',masters[model],'symbol',name,i*3,0,'R0')
                # PDK wf maps to Spectre total W; CDF w is W/fingers.
                values={'l':p['l'],'wf':p['w'],'w':p['w']/p['nf'],'fingers':p['nf'],'simM':p['m'],'model':model}
                rows=' '.join('list('+json.dumps(k)+' "string" '+json.dumps(format(v,'.17g') if isinstance(v,(float,int)) else v)+')' for k,v in values.items())
                sch.add('let((i) i='+create+' foreach(p list('+rows+') dbReplaceProp(i car(p) cadr(p) caddr(p))))')
                sch.add_net_label_to_transistor(name,drain_net='D_'+name,gate_net='G',source_net='S',body_net='B')
            terminals=['D_'+p[0] for p in prototypes]+['G','S','B']
            for j,name in enumerate(terminals):sch.add(pin(name,-2,j*1.5,'R0',direction='inputOutput'))
        callbacks=tsmc18_callbacks.invoke(client,lib,[cell],config,timeout=120)
        write_json(Path(out)/'cdf_callbacks.json',callbacks)
        readback=client.schematic.read(lib,cell,include_positions=False,param_filters=None)
        write_json(Path(out)/'prototype_readback.json',readback)
        for item in readback['instances']:
            p=item['params']
            def scalar(v):
                match=re.fullmatch(r'([0-9.eE+-]+)([munpf]?)',str(v))
                return float(match[1])*SCALE[match[2]]
            if not math.isclose(scalar(p['wf']),scalar(p['w'])*scalar(p['fingers']),rel_tol=1e-8):
                raise ValueError('CDF total/finger width contract failed')
        exported=client.schematic.export_netlist(lib,cell,Path(out)/'export',timeout=180,netlist_only=True)
        return Path(exported['input_file']).with_name('netlist'),cell
    finally:
        client.library.delete(lib,timeout=60)

def enrich(client,inputs,staged,output,env,process,remote,arguments):
    inputs,output=Path(inputs),Path(output);output.mkdir(parents=True,exist_ok=False)
    cfg=read_json(ROOT/process['enrichment']['callbacks'])
    remote=remote+'/primitive'
    runner=client.ssh_runner
    checked(runner.run_command(shlex.join(['mkdir','-p',remote+'/source']),timeout=30))
    # The complete staged include tree is small; one transfer avoids per-file
    # SSH latency for every condition without reusing native characterization.
    source_archive=output/'source_bundle.tar.gz'
    with tarfile.open(source_archive,'w:gz') as archive:
        for name in staged['sources']:archive.add(inputs/name,arcname=name,recursive=False)
    checked(runner.upload(source_archive,remote+'/source_bundle.tar.gz',timeout=30))
    checked(runner.run_command(shlex.join(['tar','-xzf',remote+'/source_bundle.tar.gz','-C',remote+'/source']),timeout=30))
    original=inspect(client,remote+'/source/'+staged['entry'],remote+'/original',output/'original',env,arguments)
    selected={}
    native=[]
    prototypes=[];bykey={}
    for name,row in original.items():
        if row.get('primitive')!='bsim4':continue
        model=re.sub(r'\.\d+$','',row['model'])
        if model not in cfg['models'].values():raise ValueError('Unqualified MOS model '+row['model'])
        p=row['parameters']
        if all(key in p for key in TAIL):native.append(name);continue
        if not all(key in p for key in PROTECTED):raise ValueError('Missing native dimension '+name)
        key=(model,*(p[k] for k in PROTECTED))
        if key not in bykey:
            prototype='M'+str(len(prototypes));bykey[key]=prototype;prototypes.append((prototype,model,p))
        selected[name]=(bykey[key],model,p)
    if not selected:
        raise ValueError('Required enrichment selected zero primitive devices; inspect coverage')
    body,cell=native_prototypes(client,prototypes,output,remote,cfg)
    checked(runner.upload(body,remote+'/devices.scs',timeout=30))
    context=output/'native_context.scs'
    drains=['D_'+p[0] for p in prototypes]
    # Unique drain nodes prevent Spectre X parallel-device merging of prototypes.
    context.write_text('simulator lang=spectre\ninclude '+json.dumps(remote+'/source/'+staged['entry'])+'\nsubckt native_devices ('+' '.join(drains+['G','S','B'])+')\ninclude '+json.dumps(remote+'/devices.scs')+'\nends native_devices\nXnative ('+' '.join(['Native'+d for d in drains]+['NativeG','0','0'])+') native_devices\n'+''.join('Vnative'+d+' (Native'+d+' 0) vsource dc=.9\n' for d in drains)+'VnativeG (NativeG 0) vsource dc=.9\n',encoding='utf-8',newline='\n')
    checked(runner.upload(context,remote+'/native_context.scs',timeout=30))
    enriched=inspect(client,remote+'/native_context.scs',remote+'/native',output/'native',env,arguments)
    changes=[]
    for name,(proto,model,before) in selected.items():
        row=enriched['Xnative.'+proto];after=row['parameters']
        if re.sub(r'\.\d+$','',row['model'])!=model:raise ValueError('Native model changed')
        for key in PROTECTED:
            if not math.isclose(before[key],after[key],rel_tol=1e-12):raise ValueError('Native effective dimension changed: '+key)
        for key in TAIL:
            if key not in after:raise ValueError('Native export omitted required parameter '+key)
            if key not in before or not math.isclose(before[key],after[key],rel_tol=1e-12,abs_tol=1e-30):
                changes.append(dict(instance=name,parameter=key,before=before.get(key),after=after[key]))
    lines=['simulator lang=spectre'];names=[]
    for i,c in enumerate(changes):
        name='msar_pdk_'+str(i);names.append(name)
        lines.append(f'{name} alter dev={json.dumps(c["instance"])} param={c["parameter"]} value={c["after"]:.17g} reelaborate=no annotate=no')
    if names:lines[-1]=lines[-1].replace('reelaborate=no','reelaborate=yes')
    (output/'pdk.scs').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    checked(runner.upload(output/'pdk.scs',remote+'/pdk.scs',timeout=30))
    applied=output/'applied.scs'
    applied.write_text('simulator lang=spectre\ninclude '+json.dumps(remote+'/pdk.scs')+'\ninclude '+json.dumps(remote+'/source/'+staged['entry'])+'\n',encoding='utf-8',newline='\n')
    checked(runner.upload(applied,remote+'/applied.scs',timeout=30))
    final=inspect(client,remote+'/applied.scs',remote+'/applied',output/'applied',env,arguments,names)
    for name,(proto,model,before) in selected.items():
        for key in (*PROTECTED,*TAIL):
            value=final[name]['parameters'][key]
            reference=enriched['Xnative.'+proto]['parameters'][key]
            if not math.isclose(value,reference,rel_tol=1e-12,abs_tol=1e-30):raise ValueError('Alter readback mismatch '+name+':'+key)
        if final[name]['model']!=original[name]['model']:raise ValueError('Alter changed model bin')
    for name in native:
        if final[name]!=original[name]:raise ValueError('Native standard cell parameters changed')
    if (output/'applied/nodes.txt').read_text()!=(output/'original/nodes.txt').read_text():
        raise ValueError('Enrichment changed original connectivity')
    report=dict(device_count=len(selected),prototype_count=len(prototypes),native_preserved_count=len(native),
        inspected_mos_count=len(selected)+len(native),change_count=len(changes),changes=changes,
        dimensions_preserved=True,connectivity_preserved=True,native_readback_match=True)
    write_json(output/'changes.json',report)
    shutil.copyfile(output/'pdk.scs',inputs/'pdk.scs')
    entry=inputs/staged['entry'];entry.write_text('simulator lang=spectre\ninclude "pdk.scs"\n'+entry.read_text(),encoding='utf-8',newline='\n')
    staged['sources'].append('pdk.scs')
    return {k:v for k,v in report.items() if k!='changes'}|{'record':str(output/'changes.json')}

"""Placement for the library-based low-power implementation.

Reuse retained instance locations in larger blocks and arrange new wrappers in
signal-flow order. Symbol terminals stay at their captured native locations.
"""
from copy import deepcopy


def layout(data, base):
    cell=data['cell']; names={i['name'] for i in data['instances']}
    pos={n:deepcopy(p) for n,p in base['drawing']['instances'].items() if n in names}
    notes=[]
    def put(name,x,y,orient='R0'):
        if name in names:pos[name]=dict(xy=[x,y],orient=orient)
    if names=={'I_cell'}:
        put('I_cell',0,0)
    elif cell=='SAR_HANDSHAKE':
        for k in range(len(names)):
            put(f'I_b{k}',3*k,0)
    elif cell=='SAR_CAPTURE_LATCH':
        put('I_latch',0,0);put('I_qb',3,0)
        notes.append((0,1.5,'Transparent while Hold is low'))
    elif cell=='SAR_FAST_SEQ':
        put('I_reset',0,3);put('I_cell',6,0)
        if 'I_gate' in names:
            put('I_db',0,-3);put('I_enable',3,-3);put('I_gate',3,0)
            notes.append((0,5,'Enable = D & !Q; clock gate latches while CP is low'))
    elif cell=='SAR_WAIT_GATE':
        put('I_stop_n',0,0);put('I_stop',3,0);put('I_gate',6,0)
        notes.append((0,2,'Z = !(Delayed*Early + Valid + Hold + Done)'))
    elif cell=='SAR_SAMPLE':
        put('I_boost',0,2);put('Mn_sample',4,0,'R270')
        notes.append((0,4,'Single bootstrap / NMOS sampling switch'))
    elif cell=='SAR_PHASE':
        put('I_clock',13,3)
        notes.extend([(0,8,'Power-on reset'),(0,4,'Clock enable / clock drive'),
                      (0,1.5,'Five-state ring'),(0,-1.5,'Sample drive')])
    elif cell=='SAR_CMP':
        # Retain the analog core placement and replace the digital sense chain.
        notes.extend([(-2,7,'PMOS input pair / regenerative latch / reset'),
                      (-2,-1,'Differential output sense'),(-2,-3,'Valid detection')])
    elif cell=='SAR_ASYNC':
        notes.extend([(0,5,'Sampling / startup / reset'),
                      (-1,-5.5,'Completion feedback / comparator clock')])
    assert set(pos)==names,(cell,'Unplaced instances',names-set(pos))
    return pos,notes

"""Placement for the accepted ADC hierarchy; no OA operations are performed here."""
from copy import deepcopy
import re
from .adc_buses import compact_signals


def fold_drivers(data):
    data = deepcopy(data)
    groups = {
        'SAR_PHASE': [('I_pre', 7, 0), ('I_final', 63, 0), ('I_ring', 3, 0)],
        'SAR_ASYNC': [('I_seq', 9, 0)],
        'MONOTONIC_SAR': [('I_out', 9, 0), ('I_bit', 1, 0)],
    }
    specifications=[(stem+f'<{high}:{low}>',[stem+str(i) for i in range(high,low-1,-1)])
                    for stem,high,low in groups.get(data['cell'],[])]
    paired={
        'SAR_BIT': [('I_select',['I_select_p','I_select_n']),
                    ('I_buf0',['I_buf_p0','I_buf_n0']),('I_buf1',['I_buf_p1','I_buf_n1'])],
        'SAR_FRONTEND': [('I_sample',['I_sp','I_sn']),('C_cross',['C_cross_p','C_cross_n'])],
        'SAR_CMP': [('I_out',['I_outp','I_outn']),('I_out1',['I_outp1','I_outn1']),
                    ('I_out2',['I_outp2','I_outn2'])],
        'SAR_PHASE': [('I_por',['I_por0','I_por1'])],
        'SAR_STARTUP': [('I_por',['I_por0','I_por1'])],
        'SAR_ASYNC': [('I_cp',['I_cp0','I_cp1'])],
        'SAR_SAMPLE_GUARD2': [('I_d',['I_d0','I_d1'])],
        'SAR_CDAC': [(f'C_weight{bit}',[f'Cp{bit}',f'Cn{bit}']) for bit in range(9,0,-1)]
                    + [('C_dummy',['Cp_dummy','Cn_dummy'])],
    }
    specifications += [(stem+'<1:0>',members) for stem,members in paired.get(data['cell'],[])]
    for array_name, member_names in specifications:
        by_name = {i['name']: i for i in data['instances']}
        members = [by_name[name] for name in member_names]
        first = deepcopy(members[0])
        assert all((i['model'], i['parameters'], i['oa_parameters']) ==
                   (first['model'], first['parameters'], first['oa_parameters']) for i in members)
        first['name'] = array_name
        first['array_members'] = [i['name'] for i in members]
        first['connections'] = {
            term: values[0] if len(set(values)) == 1 else ','.join(compact_signals(values))
            for term in first['connections']
            for values in [[i['connections'][term] for i in members]]
        }
        first['nodes'] = list(first['connections'].values())
        removed = set(first['array_members'])
        data['instances'] = [i for i in data['instances'] if i['name'] not in removed] + [first]
    return data


def placements(data):
    """Explicit functional rows, with matched P/N branches kept adjacent."""
    cell = data['cell']; out = {}
    def put(name, x, y, orient='R0'):
        out[name] = dict(xy=[x, y], orient=orient)
    def row(names, y, x=0, pitch=4):
        for index, name in enumerate(names.split()): put(name, x+index*pitch, y)
    if cell in ('SAR_DRIVE', 'SAR_DAC_DRIVE'):
        put('Mp', 0, 1); put('Mn', 0, -1)
    elif cell in ('SAR_NAND2', 'SAR_SELECT'):
        put('Mp0', 0, 1.5); put('Mp1', 2, 1.5)
        put('Mn0', 0, 0); put('Mn1', 0, -1.5)
    elif cell == 'SAR_BIAS':
        put('Mp_diode', 0, 1); put('Mn_sink', 0, -1); put('C_bias', 2, 0)
    elif cell == 'SAR_CMP':
        put('Mp_bias', 2, 5); put('Mp_clock', 2, 3.5)
        put('Mp_input_p', 0, 2);put('Mp_input_n', 6, 2,'MY')
        put('Mn_latch_p', 0, 0);put('Mn_latch_n', 6, 0,'MY')
        put('Mn_reset_p', -2, 0);put('Mn_reset_n', 8, 0,'MY')
        row('I_out<1:0> I_out1<1:0> I_out2<1:0>', -3, -2, 3.75)
        row('I_valid I_vb0 I_vb1', -6, -2, 3.75)
    elif cell in ('SAR_BOOST', 'SAR_BOOST_HI'):
        row('Mp_precharge Mp_start Mp_transfer', 2.5, 0, 2.5)
        row('Mn_reset_bottom Mn_start Mn_trackq', 0, 0, 2.5)
        put('C_boot', -2, 1.25); put('Mn_reset_gate', 7.5, 0)
        put('Mp_bottom' if cell.endswith('_HI') else 'Mn_bottom', 2.5, -2)
    elif cell == 'SAR_SAMPLE':
        row('I_boost1 I_boost2', 3, 0, 4)
        put('Mn_sample', 4, -1); put('Mp_junction', 6.5, -1)
    elif cell == 'SAR_CDAC':
        row(' '.join(f'C_weight{i}<1:0>' for i in range(9,4,-1)), 2, 0, 1.5)
        row(' '.join(f'C_weight{i}<1:0>' for i in range(4,0,-1))+' C_dummy<1:0>', -1, 0, 1.5)
    elif cell == 'SAR_FRONTEND':
        put('I_sample<1:0>', 0, 0); put('I_cdac', 5, 0)
        put('C_cross<1:0>', 2.75, 1.5)
    elif cell in ('SAR_INV', 'SAR_HANDSHAKE', 'SAR_DONE_DELAY'):
        row(' '.join(i['name'] for i in data['instances']), 0, 0, 3.5)
    elif cell == 'SAR_OUT':
        row('I_latch I_buf0 I_buf1', 0, 0, 3.5)
    elif cell == 'SAR_BIT':
        put('I_latch', 0, 0)
        row('I_select<1:0> I_buf0<1:0> I_buf1<1:0>', 0, 3.5, 2.5)
    elif cell == 'SAR_SAMPLE_GUARD2':
        put('I_d<1:0>',0,1);put('C_delay',0,-1)
        put('Mp0',3,3);put('Mp1',3,1.5)
        put('Mn0',3,-1);put('Mn1',5.5,-1);put('I_drive',8,0)
    elif cell == 'SAR_PHASE':
        put('Mp_charge', 0, 6); put('C_por', 2, 5.5)
        put('I_por<1:0>', 4, 6)
        row('I_enable I_gate I_gatebuf I_clk0', 3, 0, 4)
        put('Mp_clock_slew', 16, 4); put('Mn_clock_slew', 16, 2); put('C_clock_slew', 18, 3)
        row('I_ring<3:0> I_ring4', 0, 4, 6)
        row('I_buffer0 I_buffer1 I_buffer2 I_buffer3 I_pre<7:0> I_final<63:0>', -3, 0, 3.5)
    elif cell == 'SAR_ASYNC':
        row('I_sample_guard I_startup I_reset', 3, 0, 4)
        put('I_cp<1:0>', 13, 3)
        put('I_seq<9:0>', 8, 0)
        row('I_feedback_delay I_early I_run_nor I_clock_drive I_done_delay', -3, 0, 4)
    elif cell == 'SAR_STARTUP':
        put('Mp_charge',0,5);put('C_por',2,4.5)
        put('I_por<1:0>',4,5)
        put('I_arm',10,4);put('I_ready_inv',14,4)
        put('Mp0',7,3);put('Mp1',7,1.5)
        put('Mn0',7,0);put('Mn1',10,0);put('I_hold',14,1)
        put('I_sample_inv',0,-3)
        put('Mn_clear0',6,-4);put('Mn_clear1',6,-5.5)
        put('Mp_clear0',6,-2);put('Mp_clear1',8.5,-2)
        put('I_clear_drive',12,-3)
    elif cell in ('SAR_DFFR','SAR_ARM'):
        for x,stem in [(0,'MI31'),(2.5,'MI32'),(8,'MI13'),(26,'MI27')]:
            put(stem+'-M_u3',x,2);put(stem+'-M_u2',x,0)
        for name,x,y in [
            ('MI6',5,2),('MI7',5,3.5),('MI5',5,0),('MI4',5,-1.5),
            ('MI45',11,2),('MI43',11,3.5),('MI44',13,3.5),
            ('MI47',11,0),('MI48',11,-1.5),('MI49',11,-3),
            ('MI16',16,2),('MI15',16,0),('MI17',18.5,2),('MI18',18.5,0),
            ('MI21-M_u1',21,2),('MI21-M_u2',23,2),('MI21-M_u3',21,0),('MI21-M_u4',21,-1.5),
            ('MI14-M_u3',18.5,6),('MI14-M_u2',18.5,4),
            ('C_storage',7,-3),('C_stack',5,-3.5),('C_slave',16,-3),('C_pstack',7,4)]:put(name,x,y)
    elif cell=='SAR_DFFS':
        for x,stem in [(0,'MI55'),(2.5,'MI40'),(21,'MI25'),(24,'MI60')]:
            put(stem+'-M_u3',x,2);put(stem+'-M_u2',x,0)
        for name,x,y in [
            ('MI26',5,2),('MI28',5,3.5),('MI21',5,0),('MI19',5,-1.5),
            ('MI32-M_u1',8,2),('MI32-M_u2',10,2),('MI32-M_u3',8,0),('MI32-M_u4',8,-1.5),
            ('MI34',13,2),('MI35',13,3.5),('MI23',13,0),('MI24',13,-1.5),
            ('MI30',16,2),('MI20',16,0),('MI33',18.5,2),('MI22',18.5,0),
            ('MI31-M_u1',16,7),('MI31-M_u2',18.5,7),('MI31-M_u3',16,5),('MI31-M_u4',16,3.5),
            ('C_storage',7,-3),('C_stack',13,5),('C_pstack',5,5)]:put(name,x,y)
    elif cell == 'MONOTONIC_SAR':
        put('I_frontend', 0, 8); put('I_cmp', 6, 9); put('I_bias', 6, 13)
        row('I_phase I_inv', 4, -6, 5)
        put('I_async', 6, 4); put('I_out<9:0>', 13, 9)
        for index, name in enumerate([f'I_bit{bit}' for bit in range(9,1,-1)]+['I_bit<1:0>']):
            put(name, (index%5)*4.5, -(index//5)*4)
    else:
        # The remaining storage/logic cells have explicit matching N/P names.
        # Each pair is one functional column, in source signal order.
        stems=[]
        for inst in data['instances']:
            stem=re.sub(r'^M[np]_', '', inst['name'])
            if stem not in stems: stems.append(stem)
        for index,stem in enumerate(stems):
            for inst in data['instances']:
                if re.sub(r'^M[np]_', '', inst['name']) != stem: continue
                x=(index%6)*3; y=-(index//6)*5
                if inst['model'].startswith('pch'): y+=1
                elif inst['model'].startswith('nch'): y-=1
                put(inst['name'],x,y)
    assert set(out)=={i['name'] for i in data['instances']}, (cell, set(out) ^ {i['name'] for i in data['instances']})
    return out

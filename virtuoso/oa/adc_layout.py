"""Fold repeated native instances into ordered OA arrays."""
from copy import deepcopy
from .adc_buses import compact_signals


def fold_drivers(data):
    data = deepcopy(data)
    groups = {
        'SAR_PHASE': [('I_ring', 3, 0)],
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
        'SAR_SAMPLE_GUARD': [('I_d',['I_d0','I_d1'])],
        'SAR_CDAC': [(f'C_weight{bit}',[f'Cp{bit}',f'Cn{bit}']) for bit in range(9,0,-1)]
                    + [('C_dummy',['Cp_dummy','Cn_dummy'])],
    }
    specifications += [(stem+'<1:0>',members) for stem,members in paired.get(data['cell'],[])]
    if data['cell']=='SAR_ASYNC':
        specifications += [('I_seq_reset<9:0>',[f'I_seq{i}__I_reset' for i in range(9,-1,-1)]),
                           ('I_seq_ff<9:0>',[f'I_seq{i}__I_cell' for i in range(9,-1,-1)])]
    for array_name, member_names in specifications:
        by_name = {i['name']: i for i in data['instances']}
        if not set(member_names).intersection(by_name):
            continue
        members = [by_name[name] for name in member_names]
        first = deepcopy(members[0])
        # Differently sized library stages remain separate instances.
        if not all((i['model'], i['parameters'], i['oa_parameters']) ==
                   (first['model'], first['parameters'], first['oa_parameters']) for i in members):
            continue
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

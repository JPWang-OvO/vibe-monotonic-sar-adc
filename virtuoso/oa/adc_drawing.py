"""Terminal directions for the maintained ADC functional interfaces."""
OUTPUTS = {
    'SAR_PHASE':'Sample', 'SAR_DRIVE':'Z', 'SAR_DAC_DRIVE':'Z',
    'SAR_SAMPLE_GUARD':'Z', 'SAR_STARTUP':'Hold ClearN', 'SAR_OUT':'Q',
    'SAR_CMP':'Outp Outn Valid', 'SAR_BIAS':'Bias', 'SAR_BOOST':'Gate',
    'SAR_SAMPLE':'Gate', 'SAR_BIT':'Q Bp Bn', 'SAR_ASYNC':'ClkC Done Ck<9:0>',
    'MONOTONIC_SAR':'D<9:0> EOC',
}


def direction(cell, port):
    if port in OUTPUTS.get(cell, '').split(): return 'output'
    if cell=='SAR_CMP' and port in ('Vp','Vn','Bias'): return 'input'
    if port in ('VDD','VSS','VREFP','VREFN','VCM','Vin','Vinp','Vinn','Top','Vp','Vn') or port.startswith(('Bp','Bn')):
        return 'inputOutput'
    return 'input'

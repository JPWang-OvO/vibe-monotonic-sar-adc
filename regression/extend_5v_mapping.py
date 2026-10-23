from regression.common.project import ROOT,read_json,write_json
path=ROOT/'config/processes/tsmc18_callbacks.json';config=read_json(path)
for cell,model in [('nmos5v','nch_5'),('pmos5v','pch_5')]:
    config['models'][cell]=model
    config['callback_functions'][cell]={key:f"tsmc18rf_bsim45_{cell}_CB( '{key} )" for key in ('wf','fingers','simM','l','model')}
    if ['tsmc18',cell] not in config['groups'][0]['masters']:config['groups'][0]['masters'].append(['tsmc18',cell])
write_json(path,config)

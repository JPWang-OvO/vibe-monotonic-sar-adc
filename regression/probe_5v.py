from regression.common.project import ROOT,artifact_root,read_json,write_json
from virtuoso_bridge.env import load_vb_env
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.skill_output import parse_sexpr

load_vb_env(explicit=str(ROOT.parent.parent/'Virtuoso Bridge/.env'))
env=read_json(ROOT/'config/environments/tsmc18.local.json')
client=VirtuosoClient.from_env(profile=env['profile'],log_to_ciw=False)
report={}
try:
    for cell in ('nmos5v','pmos5v'):
        code='''let((c s) c=cdfGetBaseCellCDF(ddGetObj("tsmc18" "%s")) s=getq(c->simInfo spectre)
        list(foreach(mapcar p c->parameters list(p->name p->defValue p->callback p->paramType))
        getq(s instParameters) getq(s termOrder) getq(s componentName) getq(s propMapping)))''' % cell
        result=client.execute_skill(code,timeout=30)
        if not result.ok:raise RuntimeError(result.errors)
        report[cell]=parse_sexpr(result.output)
finally:client.close()
write_json(artifact_root()/'pdk_5v_cdf.json',report)
for cell,data in report.items():
    print(cell,[p for p in data[0] if p[0] in ('w','wf','fingers','simM','l','model','description')],data[1:])

"""Project qualification of TSMC18 CDF callbacks without N28 metadata fields.

The Bridge supplies detached-CDF evaluation and native property mappings.
This adapter validates the installed TSMC18 callback names and protects actual
Spectre width semantics (wf), fingers, length, multiplicity and model.
"""
import importlib.resources
from pathlib import Path
from virtuoso_bridge.virtuoso.schematic.cdf_callbacks import (
    CdfCallbackContract, CircuitCdfCallbackResult, _inventory_skill, _response,
    _same_value, _skill, circuit_cdf_callback_skill,
)

def invoke(client,lib,cells,config,timeout=300):
    contract=CdfCallbackContract.from_mapping(config)
    result=client.execute_skill(_inventory_skill(lib,cells,'schematic',contract),timeout=timeout)
    inventory=_response(result,'cdf-callback-inventory')
    rules={(r.master_lib,r.master_cell):r for r in contract.rules}
    plan=[]
    for row in inventory[1] or []:
        cell,name,mlib,master,view,values,callbacks,has_callbacks=row
        values,callbacks=dict(values),dict(callbacks)
        rule=rules[(mlib,master)]
        if values[contract.metadata_parameter] is not None or values[contract.version_parameter] is not None:
            raise ValueError('TSMC18 qualification expects absent N28 metadata fields')
        for key in (*rule.input_callbacks,*rule.parameters):
            expected=config['callback_functions'][master][key]
            if callbacks[key]!=expected:
                raise ValueError(f'Unexpected native callback {master}.{key}: {callbacks[key]}')
        expected_model=config['models'][master]
        if values['model']!=expected_model:raise ValueError('PDK model changed')
        protected={p:values[p] for p in (*rule.input_parameters,'model')}
        plan.append((row,rule,protected))
    if not plan:raise ValueError('No devices selected for required native CDF processing')
    resource=importlib.resources.files('virtuoso_bridge.virtuoso.schematic.resources')/'CCSinvokeCdfCallbacks_v1.16.il'
    with importlib.resources.as_file(resource) as path:
        loaded=client.load_il(Path(path),timeout=timeout)
    if not loaded.ok:raise RuntimeError(loaded.errors)
    result=client.execute_skill(circuit_cdf_callback_skill(lib,plan),timeout=timeout)
    proposed=_response(result,'cdf-callback-proposals')[1] or []
    if len(proposed)!=len(plan):raise ValueError('Incomplete CDF processing')
    changes={}
    for (row,rule,before),(identity,ok,after,updates) in zip(plan,proposed):
        if list(row[:5])!=identity or not ok:raise ValueError('Native CDF callback failed: '+str(identity))
        after=dict(after)
        different={p:(v,after[p]) for p,v in before.items() if not _same_value(v,after[p])}
        if different:raise ValueError('CDF changed protected source geometry: '+str(different))
        changes.setdefault(row[0],[]).append((row[1],updates or []))
    commands=[]
    for cell,updates in changes.items():
        # Same save operation as Bridge invoke_circuit_cdf_callbacks; no PDK writes.
        commands.append(f'''cv=dbOpenCellViewByType({_skill(lib)} {_skill(cell)} "schematic" "schematic" "a")
          unless(cv error("Callback schematic cannot be saved"))
          unwindProtect(progn(
            foreach(row {_skill(updates)}
              inst=car(setof(i cv~>instances i~>name==car(row)))
              unless(inst error("Callback instance missing during save"))
              foreach(p cadr(row) dbReplaceProp(inst car(p) cadr(p) caddr(p))))
            schCheck(cv) dbSave(cv)) dbClose(cv))''')
    saved=client.execute_skill('let((cv inst row p) '+' '.join(commands)+' t)',timeout=timeout)
    if not saved.ok:raise RuntimeError(saved.errors)
    return dict(processed_cells=len(changes),processed_instances=len(plan),master_metadata=inventory[2],
        qualification='Explicit installed callback strings, native propMapping, protected wf/l/fingers/simM/model',
        proposals=proposed)

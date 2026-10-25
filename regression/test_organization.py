"""Offline contracts for the consolidated flows, studies and measurement probes."""
import re
import tempfile
import unittest
from pathlib import Path

from regression.common.project import ROOT, read_json
from regression.common.plans import load_plan
from regression.common.variants import sources as variants
from regression.common.sources import stage
from regression.common.measure import criterion
from virtuoso.oa.adc_source import current_hierarchy, assignments
from virtuoso.oa.comparison import spectre_document

FLOW = ROOT/'regression/systems/monotonic_sar/flows/acceptance/flow.json'


class OrganizationTests(unittest.TestCase):
    def test_acceptance_matrix_and_baseline(self):
        flow = load_plan(FLOW)
        expected = {(c,t,k,n) for c,t in [('tt',25),('ss',-40),('ss',125),('ff',-40),('ff',125)]
                    for k in (3,51) for n in (False,True)}
        actual = {(c['corner'],c['tokens']['TEMP'],c['k'],c['noise']) for c in flow['conditions']}
        self.assertEqual(actual, expected)
        self.assertEqual(len(flow['conditions']),20)
        baseline = {r['condition']:r for r in read_json(ROOT/flow['baseline'])['cases']}
        self.assertEqual(set(baseline),{c['id'] for c in flow['conditions']})
        for c in flow['conditions']:
            self.assertEqual(c['criteria']['sndr_db']['min'],57 if c['k']==3 else 56.5)
            self.assertEqual('core_power_w' in c['criteria'],c['corner']=='tt')
            self.assertTrue(all(criterion(baseline[c['id']]['metrics'][n],r) for n,r in c['criteria'].items()))
        self.assertEqual(flow['measurement']['read_offset_s'],18e-9)

    def test_study_edits_and_dependency_closure(self):
        for plan_path in read_json(ROOT/'project.json')['studies']:
            plan = load_plan(ROOT/plan_path)
            for condition in plan['conditions']:
                generated = variants(condition)
                with tempfile.TemporaryDirectory() as temp:
                    staged = stage(ROOT/plan['testbench'],ROOT,Path(temp),
                                   dict(condition['tokens'],MODEL_SETUP=''),
                                   cell_views=condition['cell_views'],overrides=generated)
                    definitions = {}
                    for name in staged['sources']:
                        text = (Path(temp)/name).read_text()
                        for include in re.findall(r'(?m)^include "([^"]+)"',text):
                            self.assertTrue((Path(temp)/include).is_file(),include)
                        if name == staged['entry']:
                            continue
                        subcircuits = spectre_document(text)['subcircuits']
                        self.assertFalse(set(definitions)&set(subcircuits))
                        definitions.update(subcircuits)
                    for cell,text in generated.items():
                        parsed=spectre_document(text)['subcircuits'][cell]
                        for edit in condition['source_edits']:
                            if edit['cell']!=cell:continue
                            for instance in edit.get('instances',[]):
                                tokens=parsed['statements'][instance]
                                params=assignments(tokens[tokens.index(')')+2:])
                                self.assertEqual(params[edit['parameter']],edit['value'])
                    if 'feedback_stages' in condition['topology']:
                        self.assertEqual(len(re.findall(r'(?m)^I_feedback_delay__I_b\d+',generated['SAR_ASYNC'])),
                                         condition['topology']['feedback_stages'])

    def test_saved_signal_and_current_probes_resolve(self):
        flow=load_plan(FLOW)
        definitions=current_hierarchy()
        normalized=lambda name:name.replace('\\<','').replace('\\>','').replace('<','').replace('>','')
        def resolve(probe):
            path=probe.split('.')
            self.assertEqual(path.pop(0),'I_adc')
            cell='MONOTONIC_SAR'
            for part in path[:-1]:
                cell=next(i['model'] for i in definitions[cell]['instances'] if i['name']==part)
            last=path[-1]
            if ':' in last:
                instance,terminal=last.split(':')
                child=next(i['model'] for i in definitions[cell]['instances'] if i['name']==instance)
                self.assertLessEqual(int(terminal),len(definitions[child]['ports']))
                self.assertGreater(int(terminal),0)
            else:
                nets={normalized(n) for i in definitions[cell]['instances'] for n in i['nodes']}
                self.assertIn(normalized(last),nets)
        text=(ROOT/flow['testbench']).read_text()
        saved=[p for line in text.splitlines() if line.startswith('save ') for p in line.split()[1:]]
        for probe in saved:
            if probe.startswith('I_adc.'):resolve(probe)
        cfg=flow['measurement']
        currents=cfg['output_buffer_currents']+[p for group in cfg['module_power_currents'].values() for p in group['currents']]
        for probe in currents:
            self.assertIn(probe,saved)
            resolve(probe)

    def test_case_selection_is_explicit(self):
        self.assertEqual(len(load_plan(FLOW,['tt_25_k3_quiet'])['conditions']),1)
        with self.assertRaisesRegex(ValueError,'Unknown conditions'):
            load_plan(FLOW,['old_candidate'])


if __name__=='__main__':
    unittest.main()

import copy
import unittest
from unittest.mock import patch

from regression.common.plans import load_plan
from regression.common.project import ROOT, read_json
from virtuoso.ade.plan import compile_flow, testbench


class MaestroPlanTests(unittest.TestCase):
    def setUp(self):
        self.paths = [ROOT/p for p in read_json(ROOT/'project.json')['flows']]
        self.system = next(p for p in self.paths if 'systems' in p.parts)

    def test_native_matrix_covers_all_cases_once(self):
        plans = [compile_flow(path) for path in self.paths]
        self.assertEqual(sum(len(p['tests']) for p in plans), 4)
        self.assertEqual(sum(len(p['points']) for p in plans), 30)
        for path, plan in zip(self.paths, plans):
            source = load_plan(path)
            self.assertEqual({p['condition']['id'] for p in plan['points']},
                             {c['id'] for c in source['conditions']})
            self.assertEqual(len(plan['points']), len({p['id'] for p in plan['points']}))
        system = plans[0]
        self.assertEqual([len(t['variables']['fin']) for t in system['tests']], [2, 2])

    def test_incomplete_cartesian_matrix_is_rejected(self):
        flow = load_plan(self.system)
        flow['conditions'].pop()
        with patch('virtuoso.ade.plan.load_plan', return_value=flow):
            with self.assertRaisesRegex(ValueError, 'Corner/sweep product differs'):
                compile_flow(self.system)

    def test_overlapping_test_groups_are_rejected(self):
        flow = load_plan(self.system)
        flow['ade']['tests'].append(copy.deepcopy(flow['ade']['tests'][0]))
        with patch('virtuoso.ade.plan.load_plan', return_value=flow):
            with self.assertRaisesRegex(ValueError, 'more than one test'):
                compile_flow(self.system)

    def test_different_views_cannot_be_hidden_in_sweep(self):
        flow = load_plan(self.system)
        flow['conditions'][0]['cell_views'] = {'MONOTONIC_SAR': 'pex'}
        with patch('virtuoso.ade.plan.load_plan', return_value=flow):
            with self.assertRaisesRegex(ValueError, 'separate tests'):
                compile_flow(self.system)

    def test_fixed_comparator_pwl_is_preserved(self):
        path = next(p for p in self.paths if 'sar_cmp' in p.parts)
        tb = testbench(ROOT/load_plan(path)['testbench'])
        for name in ('Vinp', 'Vinn'):
            row = next(r for r in tb['instances'] if r['name'] == name)
            pairs = row['parameters']['wave'].strip('[]').split()
            self.assertEqual(len(pairs), 82)
            self.assertEqual(pairs[-2], '2.4002e-07')


if __name__ == '__main__':
    unittest.main()

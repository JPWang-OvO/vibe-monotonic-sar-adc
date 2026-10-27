import copy
import unittest
import tempfile
from pathlib import Path
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

    def test_worker_budget_is_checked_before_preparation(self):
        from virtuoso.ade.rebuild import prepare
        limit = read_json(ROOT/'config/run_budget.json')['max_workers']
        for workers in (0, limit+1):
            with self.subTest(workers=workers), self.assertRaisesRegex(ValueError, 'run budget'):
                prepare(self.system, 'invalid_budget', None, 'UNUSED', '/unused', workers)

    def test_bus_ports_keep_fixed_tb_bit_order(self):
        from virtuoso.ade.native import connections
        self.assertEqual(connections(['A', 'D<2:0>', 'VSS'], ['a', 'D2', 'D1', 'D0', '0']),
                         {'A':'a', 'D<2:0>':'D2,D1,D0', 'VSS':'gnd!'})

    def test_native_save_paths_cover_buses_and_renamed_sources(self):
        plan = compile_flow(self.system)
        mapping = dict(zip(plan['tb']['save'], plan['native_save']))
        self.assertEqual(mapping['VDD:p'], 'VDD_SRC:p')
        self.assertEqual(mapping['I_adc.Bp9'], r'I_adc.Bp\<9\>')
        self.assertEqual(mapping['I_adc.I_out0:4'], r'I_adc.I_out\<0\>:4')
        nodes = {node for row in plan['tb']['instances'] for node in row['nodes']}
        self.assertFalse({row['name'] for row in plan['tb']['instances']} & nodes)

    def test_tb_comparison_ignores_descended_subcircuits(self):
        from virtuoso.ade.verify import verify_tb
        tb = dict(instances=[dict(name='I_dut', nodes=['in','out'], model='DUT', parameters={})])
        verify_tb(tb, 'subckt DUT in out\nR (in out) resistor r=1k\nends DUT\nI_dut (in out) DUT\n')
        with self.assertRaisesRegex(ValueError, 'connection/model'):
            verify_tb(tb, 'I_dut (out in) DUT\n')

    def test_psf_names_map_native_traces_to_measurement_names(self):
        from regression.common.psf import read_psf
        text = 'TRACE\n"I_adc.Bp<9>" "V"\nVALUE\n"time" 0\n"I_adc.Bp<9>" 1.8\nEND\n'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'tran'
            path.write_text(text)
            self.assertEqual(read_psf(path, name_map={'I_adc.Bp<9>':'I_adc.Bp9'}),
                             {'time':[0.0], 'I_adc.Bp9':[1.8]})


if __name__ == '__main__':
    unittest.main()

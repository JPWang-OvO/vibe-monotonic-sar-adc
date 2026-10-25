"""Exercise public entries and server packaging without launching EDA tools."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from regression.common.plans import load_plan
from regression.common.project import ROOT, read_json
from regression.common.runner import prepare
from regression.common.measure import measure
from regression.blocks.sar_cmp.studies.noise.stimulus import trial_points


class ExecutionContractTests(unittest.TestCase):
    def test_all_public_entries_compile_their_own_plan(self):
        project = read_json(ROOT / 'project.json')
        with tempfile.TemporaryDirectory() as temporary:
            for index, relative in enumerate(project['flows'] + project['studies']):
                path = ROOT / relative
                condition = load_plan(path)['conditions'][0]['id']
                module = path.with_name('run').relative_to(ROOT).as_posix().replace('/', '.')
                output = Path(temporary) / str(index)
                result = subprocess.run([sys.executable, '-m', module, 'compile',
                                         '--condition', condition, '--output', str(output)],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                plan = read_json(output / 'plan.json')
                self.assertEqual(Path(plan['plan']), path)
                self.assertEqual([row['id'] for row in plan['cases']], [condition])
                self.assertFalse((output / 'batch.json').exists())

    def test_prepare_packages_importable_server_measurements(self):
        project = read_json(ROOT / 'project.json')
        plans = [ROOT / path for path in project['flows'] + project['studies']]
        environment = dict(profile='offline_test', remote_runs='/offline/runs',
                           server_python='/usr/bin/python3', spectre='/eda/spectre',
                           model_files={'tsmc18': '/pdk/models.scs'})
        original_load = load_plan

        def first_case(path, selected):
            plan = original_load(path, selected)
            plan['conditions'] = plan['conditions'][:1]
            return plan

        with tempfile.TemporaryDirectory() as temporary:
            with patch('regression.common.runner.environment', return_value=environment), \
                 patch('regression.common.runner.artifact_root', return_value=Path(temporary)), \
                 patch('regression.common.runner.load_plan', side_effect=first_case), \
                 patch('regression.common.enrichment.enrich', return_value={'test_stub': True}) as enrich:
                folder = prepare(plans, 'unused.json', 'execution_contract', workers=2)
            batch = read_json(folder / 'batch.json')
            self.assertEqual(len(batch['cases']), 7)
            self.assertEqual(enrich.call_count, 7)
            for case in batch['cases']:
                inputs = folder / 'cases' / case['id'] / 'inputs'
                self.assertTrue((inputs / case['sources']['entry']).is_file())
                self.assertIn('+preset=ax', case['command'])
                self.assertIn('+mt=8', case['command'])
                self.assertEqual(case['criteria'], case['condition']['criteria'])
            # Isolated Python can see only the prepared package, not this checkout.
            code = '''import sys, importlib, json
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from regression.common import server
from regression.common.measure import MEASUREMENT_MODULES
root = Path(sys.argv[1]).resolve()
for name in MEASUREMENT_MODULES.values():
    module = importlib.import_module(name)
    assert Path(module.__file__).resolve().is_relative_to(root)
    assert callable(module.measure)
print(json.dumps(sorted(MEASUREMENT_MODULES)))
'''
            result = subprocess.run([sys.executable, '-I', '-c', code, str(folder)],
                                    cwd=temporary, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)), 4)

    def test_noise_sequence_matches_every_testbench_pwl_trial(self):
        plan = load_plan(ROOT / 'regression/blocks/sar_cmp/studies/noise/study.json')
        cfg = plan['measurement']
        points = trial_points(cfg['sequence'])
        self.assertEqual(len(points), 3456)
        deck = (ROOT / plan['testbench']).read_text().replace('\\\n', ' ')
        for source, sign in [('Vinp', 1), ('Vinn', -1)]:
            wave = re.search(rf'{source} .*?wave=\[([^]]+)\]', deck).group(1)
            numbers = [float(token) for token in wave.split()]
            self.assertEqual(len(numbers), 2 + 4 * len(points))
            for index, point in enumerate(points):
                at, previous, settled, actual = numbers[2 + 4*index:6 + 4*index]
                expected = point['common_mode_v'] + sign * point['differential_v'] / 2
                self.assertAlmostEqual(actual, expected, delta=1e-12)
                self.assertAlmostEqual(settled - at, 20e-12, delta=1e-16)
                decision = cfg['start_s'] + index * cfg['period_s']
                self.assertGreater(decision, settled)
                self.assertAlmostEqual(decision - at, 1.01e-9, delta=1e-16)

    def test_noise_dispatch_measures_the_compact_sequence(self):
        plan = load_plan(ROOT / 'regression/blocks/sar_cmp/studies/noise/study.json')
        cfg = plan['measurement']
        wave = {name: [] for name in ('time', 'Outp', 'Outn', 'Valid', 'VDD_SRC:p')}
        for index, point in enumerate(trial_points(cfg['sequence'])):
            start = cfg['start_s'] + index * cfg['period_s']
            positive = point['differential_v'] > 0
            for dt, active in [(-.4e-9, False), (-.2e-9, False), (.4e-9, True),
                               (1.9e-9, True), (2.1e-9, False)]:
                wave['time'].append(start + dt)
                wave['Outp'].append(1.8 if not active or positive else 0)
                wave['Outn'].append(1.8 if not active or not positive else 0)
                wave['Valid'].append(1.8 if active else 0)
                wave['VDD_SRC:p'].append(-1e-6)
        with patch('regression.blocks.sar_cmp.studies.noise.measure.read_psf', return_value=wave):
            result = measure(dict(measurement=cfg, criteria={}), Path('unused'))
        self.assertEqual(result['metrics']['trials'], 3456)
        for key in ('unresolved', 'valid_late', 'reset_errors'):
            self.assertEqual(result['metrics'][key], 0)
        self.assertEqual(len(result['curves']), 3)
        for curve in result['curves']:
            self.assertEqual(len(curve['points']), 9)
            for row in curve['points']:
                self.assertEqual(row['trials'], 128)
                self.assertEqual(row['ones'], 128 if row['differential_v'] > 0 else 0)
        self.assertTrue(result['functional_pass'])
        self.assertIsNone(result['performance_pass'])


if __name__ == '__main__':
    unittest.main()

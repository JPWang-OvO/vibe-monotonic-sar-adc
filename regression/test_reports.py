"""Report acceptance requires complete results and the selected flow contract."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from regression.common.project import ROOT, read_json, write_json
from regression.common.plans import load_plan
from regression.common.study import summarize
from regression.systems.monotonic_sar.acceptance.report import report

FLOW = ROOT/'regression/systems/monotonic_sar/flows/acceptance/flow.json'


class ReportTests(unittest.TestCase):
    def test_acceptance_requires_complete_matching_successful_cases(self):
        flow = load_plan(FLOW)
        baseline = {r['condition']: r['metrics'] for r in read_json(ROOT/flow['baseline'])['cases']}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            cases, results = [], []
            for condition in flow['conditions']:
                cid = condition['id']
                cases.append(dict(id=cid, flow=FLOW.relative_to(ROOT).as_posix(), condition=condition,
                                  measurement=flow['measurement'], criteria=condition['criteria'],
                                  simulator=flow['simulator'], sources=dict(entry='tb.scs', sources=['tb.scs','dut.scs'])))
                results.append(dict(case=cid, metrics=baseline[cid], execution_pass=True,
                                    log_audit={'pass':True}, measurement_pass=True))
                inputs = folder/'cases'/cid/'inputs'; inputs.mkdir(parents=True)
                (inputs/'dut.scs').write_text('same DUT')
            write_json(folder/'batch.json', {'cases':cases})
            write_json(folder/'summary.json', {'cases':results})
            self.assertTrue(report(FLOW,[folder])['all_electrical_pass'])
            for failure in ('execution_pass','measurement_pass','log_audit','metrics','missing'):
                changed=deepcopy(results)
                if failure=='missing':changed.pop()
                elif failure=='log_audit':changed[0][failure]['pass']=False
                elif failure=='metrics':changed[0][failure]['sndr_db']=0
                else:changed[0][failure]=False
                write_json(folder/'summary.json', {'cases':changed})
                with self.subTest(failure=failure):
                    self.assertFalse(report(FLOW,[folder])['all_electrical_pass'])
            write_json(folder/'summary.json', {'cases':results})
            (inputs/'dut.scs').write_text('different DUT')
            self.assertFalse(report(FLOW,[folder])['all_electrical_pass'])
            cases[0]['measurement']=dict(cases[0]['measurement'],read_offset_s=0)
            write_json(folder/'batch.json', {'cases':cases})
            with self.assertRaises(AssertionError):report(FLOW,[folder])

    def test_study_ranks_feasible_points_by_worst_selected_case(self):
        study='regression/systems/monotonic_sar/studies/comparator/study.json'
        cases=[]; results=[]
        for point, powers in [(1,[2.,3.]),(2,[1.,4.]),(3,[.5,.6]),(4,[.1,None])]:
            for corner,power in enumerate(powers):
                cid=f'{point}_{corner}'
                cases.append(dict(id=cid,flow=study,condition={'study_parameters':{'input_um':point}}))
                if power is not None:
                    results.append({'case':cid,'measurement_pass':True,'pass':point!=3,
                                    'metrics':{'core_power_w':power}})
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            write_json(folder/'batch.json',{'cases':cases});write_json(folder/'summary.json',{'cases':results})
            rows=summarize(folder)['points']
            self.assertEqual([r['parameters']['input_um'] for r in rows],[1,2,3,4])
            self.assertEqual([r['worst_objective'] for r in rows],[3.,4.,.6,None])
            self.assertFalse(rows[-1]['complete']);self.assertFalse(rows[2]['feasible'])


if __name__=='__main__':unittest.main()

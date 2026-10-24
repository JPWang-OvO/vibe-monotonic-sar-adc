"""Focused checks of the standalone binomial noise estimator."""
import math
import unittest
from regression.systems.monotonic_sar.analysis.measure_cmp_noise import fit_probability


class ProbabilityFitTest(unittest.TestCase):
    def test_known_transition(self):
        offset=.00023;sigma=.00071;n=100000
        rows=[dict(differential_v=x,ones=round(n*.5*math.erfc(-(x-offset)/sigma/math.sqrt(2))),resolved=n)
              for x in (-.003,-.002,-.001,-.0005,0,.0005,.001,.002,.003)]
        fit=fit_probability(rows)
        self.assertTrue(fit['identifiable'])
        self.assertAlmostEqual(fit['offset_v'],offset,delta=2e-7)
        self.assertAlmostEqual(fit['sigma_v'],sigma,delta=2e-7)

    def test_hard_step_is_not_noise_estimate(self):
        rows=[dict(differential_v=x,ones=128 if x>0 else 0,resolved=128) for x in (-.001,0,.001)]
        self.assertFalse(fit_probability(rows)['identifiable'])


if __name__=='__main__':unittest.main()

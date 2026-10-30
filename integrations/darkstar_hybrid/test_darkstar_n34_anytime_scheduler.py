#!/usr/bin/env python3
"""Pre-freeze exact resumable Brent tests and public-only anytime factor controls."""
import inspect
import math
import unittest
from integrations.darkstar_hybrid import darkstar_n34_anytime_scheduler as s
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr
from simulation.ptp_hybrid import kernel

class TestN34Anytime(unittest.TestCase):
    def test_frozen_policy_and_public_arguments(self):
        self.assertEqual(tuple(inspect.signature(s.factor_public).parameters),("n","method"))
        self.assertEqual(s.METHODS,("A","B","F","Q","W","L","M"))
        self.assertEqual(s.BRENT_RUNS,((1,2,1024),(3,3,512)))
        self.assertEqual(s.BRENT_C1_CHECKPOINTS,(96,384,1024))
        self.assertEqual(s.QR_SCHEDULE,((8,72),(72,200),(200,640)))
        self.assertEqual(s.QR_TOTAL_ROOT_CAP,64)
        self.assertEqual(s.FERMAT_COUNT,8)

    def test_uninterrupted_equal_resumed_exact_factor_and_counts(self):
        numbers=(209,713,781,4703*10477,8377*14323,7334956339,8251204289,7294912013)
        for n in numbers:
            for c,seed,budget,checkpoints in ((1,2,1024,(96,384,1024)),
                                               (3,3,512,(96,256,512))):
                with self.subTest(n=n,c=c):
                    full=s.BrentState(n,c,seed,budget)
                    single=full.run_until(budget)
                    paused=s.BrentState(n,c,seed,budget)
                    seen=0
                    for target in checkpoints:
                        z=paused.run_until(target)
                        self.assertGreaterEqual(z["cumulative_squarings"],seen)
                        self.assertLessEqual(z["cumulative_squarings"],target)
                        seen=z["cumulative_squarings"]
                    self.assertEqual(paused.factors,full.factors)
                    self.assertEqual(dict(paused.ops),dict(full.ops))
                    self.assertEqual(paused.phase,full.phase)
                    self.assertEqual(paused.done,full.done)
                    self.assertLessEqual(paused.ops["modular_squarings"],budget)
                    if paused.factors:
                        self.assertEqual(math.prod(paused.factors),n)
                    self.assertEqual(single["cumulative_operations"],dict(full.ops))

    def test_all_complete_classical_branches(self):
        for n in (209,713,781,4703*10477,8377*14323,7334956339,8251204289):
            expected=list(kernel.wheel210_factor(n).factors)
            for method in ("A","B","F","Q","W","L"):
                with self.subTest(N=n,arm=method):
                    z=s.factor_public(n,method)
                    self.assertEqual(z["factors"],expected)
                    self.assertTrue(z["only_public_N_used"])
                    self.assertTrue(z["no_factor_or_stratum_or_order_input"])
                    self.assertTrue(z["complete"])
                    self.assertLessEqual(z["operation_counts"].get("Brent_c1_modular_squarings",0),1024)
                    self.assertLessEqual(z["operation_counts"].get("Brent_c3_modular_squarings",0),512)
                    self.assertLessEqual(z["operation_counts"].get("QR_exact_square_root_tests",0),64)
                    self.assertLessEqual(z["operation_counts"].get("QR_midpoint_positions",0),632)

    def test_exact_QR_and_near_Fermat_shortcut(self):
        n=209
        z=s.factor_public(n,"A")
        self.assertEqual(z["successful_stage"],"early_plain_fermat8")
        self.assertFalse(any(x["stage"]=="QR_public_per_N_mask_setup" for x in z["stages"]))
        for n in (4703*10477,8377*14323):
            control=qr.ordinary_fermat_window(n,4095)
            candidate=qr.fast_public_midpoint_factor(n,qr.WHEELS[255255],4095)
            self.assertEqual(control["factors"],candidate["factors"])
            self.assertEqual(control["found_at_offset"],candidate["found_at_offset"])
            self.assertLessEqual(candidate["exact_square_root_tests"],control["exact_square_root_tests"])

if __name__=="__main__":
    unittest.main(verbosity=2)

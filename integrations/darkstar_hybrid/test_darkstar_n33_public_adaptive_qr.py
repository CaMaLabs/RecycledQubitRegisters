#!/usr/bin/env python3
"""Public-only adaptive N33 QR routing: fixed spec and exact factoring controls."""
import inspect
import math
import unittest
from integrations.darkstar_hybrid import darkstar_n33_public_adaptive_qr as p
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr
from simulation.ptp_hybrid import kernel

class TestPublicAdaptiveQR(unittest.TestCase):
    def test_immutable_policy_and_public_signature(self):
        self.assertEqual(tuple(inspect.signature(p.public_factor).parameters),("n","method"))
        self.assertEqual(p.POLICY,"darkstar_public_adaptive_qr_33_v1_20261029")
        self.assertEqual(p.METHODS,("A","B","F","Q","W","L","M"))
        self.assertEqual(p.FERMAT_EARLY,8)
        self.assertEqual(p.PILOT_START,8)
        self.assertEqual(p.PILOT_LENGTH,64)
        self.assertEqual(p.EXTENDED_END_OFFSET,639)
        self.assertEqual(p.QUALIFYING_PILOT_MAX,2)
        self.assertEqual(p.QR_MAX_SQUARE_TESTS,64)
        self.assertEqual(p.BRENT_BUDGETS,((1,2,1024),(3,3,512)))

    def test_six_complete_public_methods_return_true_factors(self):
        cases=((11,19),(23,31),(29,71),(4703,10477),
               (8377,14323),(1009,2017),(7001,8009))
        for a,b in cases:
            n=a*b
            truth=list(kernel.wheel210_factor(n).factors)
            for method in ("A","B","F","Q","W","L"):
                with self.subTest(N=n,method=method):
                    z=p.public_factor(n,method)
                    self.assertEqual(z["factors"],truth)
                    self.assertTrue(z["complete"])
                    self.assertTrue(z["public_N_only"])
                    self.assertFalse(z["has_private_factor_or_stratum_input"])
                    self.assertLessEqual(z["operations"].get("rho_modular_squarings",0),1536)
                    for step in z["stages"]:
                        if step["stage"] in ("public_QR_64_position_pilot","extended_QR_midpoint_scan"):
                            self.assertLessEqual(step["exact_square_root_tests"],64)

    def test_early_fermat_no_qr_setup_and_real_qr_logic(self):
        near=p.public_factor(209,"A")
        self.assertEqual(near["successful_stage"],"plain_fermat_first_8")
        self.assertFalse(any(z["stage"]=="QR_public_mask_setup" for z in near["stages"]))
        for n in (4703*10477,8377*14323):
            z=p.public_factor(n,"A")
            for stage in z["stages"]:
                if stage["stage"]=="public_eligibility_decision":
                    self.assertEqual(stage["extend"],stage["qualifying_pilot_positions"]<=2)
                if stage["stage"] in ("public_QR_64_position_pilot","extended_QR_midpoint_scan"):
                    if stage["factors"]:
                        self.assertEqual(math.prod(stage["factors"]),n)

    def test_midpoint_pruner_math_no_factor_elimination(self):
        for n in (209,713,4703*10477,8377*14323):
            plain=qr.ordinary_fermat_window(n,4095)
            filtered=qr.fast_public_midpoint_factor(n,qr.WHEELS[255255],4095)
            self.assertEqual(plain["factors"],filtered["factors"])
            self.assertEqual(plain["found_at_offset"],filtered["found_at_offset"])
            self.assertLessEqual(filtered["exact_square_root_tests"],plain["exact_square_root_tests"])

if __name__=="__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""No-hidden-factor N32 classical controls and exact PTP-pruner unit tests."""
import inspect
import math
import unittest
from integrations.darkstar_hybrid import darkstar_n32_separation_vs_brent as b
from integrations.darkstar_hybrid import darkstar_n32_separation_manifest as pop
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr

class TestN32Controls(unittest.TestCase):
    def test_frozen_budgets(self):
        self.assertEqual(b.RHO_BUDGETS,((1,2,1024),(3,3,512)))
        self.assertEqual(b.QR_OFFSET,2047)
        self.assertEqual(b.QR_SQUARES,96)
        self.assertEqual(b.EARLY_SQUARES,8)
        self.assertEqual(b.REPEATS,9)
        self.assertEqual(tuple(inspect.signature(b.factor_public).parameters),("n","method"))
        self.assertEqual(pop.stratum_for(0),"near_0_8")
        self.assertEqual(pop.stratum_for(100),"middle_64_640")
        self.assertEqual(pop.stratum_for(4096),"far_4096_16384")
        self.assertIsNone(pop.stratum_for(9))

    def test_all_complete_methods_recover_without_pq(self):
        for p,q in ((11,19),(23,31),(29,71),(4703,10477),(8377,14323),(1009,2017)):
            n=p*q
            for name in ("B","F","Q","FQ","wheel210","PTP_LFK"):
                z=b.factor_public(n,name)
                self.assertEqual(z["factors"],[p,q],(n,name))
                self.assertTrue(z["complete"])
                if name in ("B","F","Q","FQ"):
                    self.assertLessEqual(z["operations"].get("rho_modular_squarings",0),1536)
                for item in z["stages"]:
                    if item["stage"]=="QR_255255":
                        self.assertLessEqual(item["scanned_midpoint_positions"],2048)
                        self.assertLessEqual(item["exact_square_root_tests"],96)
                        self.assertTrue(item["no_private_prime_factors_or_order_used"])

    def test_qr_is_exact_necessary_condition(self):
        for n in (209,713,4703*10477,8377*14323):
            old=qr.ordinary_fermat_window(n,4095)
            pruned=qr.fast_public_midpoint_factor(n,qr.WHEELS[255255],4095)
            self.assertEqual(old["factors"],pruned["factors"])
            self.assertEqual(old["found_at_offset"],pruned["found_at_offset"])
            self.assertLessEqual(pruned["exact_square_root_tests"],old["exact_square_root_tests"])
            self.assertTrue(pruned["no_private_prime_factors_or_order_used"])

if __name__=="__main__":
    unittest.main(verbosity=2)

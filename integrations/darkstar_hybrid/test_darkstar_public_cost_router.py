#!/usr/bin/env python3
"""Standalone frozen public-only router structural correctness tests. ZERO QPU."""
import inspect
import math
import unittest
from integrations.darkstar_hybrid import darkstar_public_cost_router as p
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr
from simulation.ptp_hybrid import kernel

class PublicCostRouterTests(unittest.TestCase):
    def test_public_only_signature_and_fixed_policy(self):
        self.assertEqual(tuple(inspect.signature(p.public_router).parameters),("n",))
        self.assertEqual(p.EARLY_FERMAT_TESTS,8)
        self.assertEqual(p.QR_MAX_OFFSET,127)
        self.assertEqual(p.QR_MAX_SQUARE_TESTS,8)
        self.assertEqual(p.RHO_SQUARING_BUDGETS,((1,2,256),(3,3,128)))
        self.assertEqual(p.RHO_BLOCK,16)
        self.assertEqual(sum(z[2] for z in p.RHO_SQUARING_BUDGETS),384)

    def test_known_composites_correct_and_full_fallback(self):
        for n in (15,21,35,77,209,713,781,10403,1009*2017,4703*10477,8377*14323):
            r=p.public_router(n)
            self.assertTrue(r["success"],n)
            self.assertEqual(math.prod(r["factors"]),n)
            self.assertEqual(r["factors"],list(kernel.wheel210_factor(n).factors))
            self.assertFalse(r["order_or_factors_used_for_routing"])
            self.assertFalse(r["uses_quantum_hardware"])
            self.assertLessEqual(r["operation_totals"].get("rho_modular_squarings",0),384)
            for z in r["stages"]:
                if z["stage"]=="restored_QR_255255_bounded":
                    self.assertLessEqual(z["scanned_midpoint_positions"],128)
                    self.assertLessEqual(z["exact_square_root_tests"],8)

    def test_expected_early_fermat_and_small_divisions(self):
        self.assertEqual(p.early_fermat(209)["factors"],[11,19])
        self.assertEqual(p.early_fermat(713)["factors"],[23,31])
        self.assertEqual(p.public_router(35)["method"],"early_fermat_8")
        self.assertEqual(p.public_router(3*101)["method"],"public_wheel_small_prime")
        self.assertEqual(p.public_router(3*101)["factors"],[3,101])

    def test_rho_public_only_hard_bound(self):
        for n in (1009*2017,4703*10477,8377*14323):
            for c,y,limit in p.RHO_SQUARING_BUDGETS:
                x=p.brent_attempt(n,c,y,limit)
                self.assertLessEqual(x["ops"].get("modular_squarings",0),limit)
                if x["factors"]:
                    self.assertEqual(math.prod(x["factors"]),n)
                self.assertGreaterEqual(x["ops"].get("gcd_calls",0),1)

    def test_necessary_residue_pruning_and_no_invalid_factor_loss(self):
        for n in (209,713,781,4703*10477):
            truth=kernel.wheel210_factor(n).factors
            z=qr.fast_public_midpoint_factor(n,qr.WHEELS[255255],max_offset=4095)
            self.assertEqual(z["factors"],list(truth))
            self.assertTrue(z["no_private_prime_factors_or_order_used"])

    def test_proximity_heuristic_is_public_comparison_only(self):
        for n in (209,713,781,4703*10477,8377*14323):
            r=p.public_router(n)
            for z in r["stages"]:
                if z["stage"]=="public_QR_route_decision":
                    s=qr.ceil_sqrt(n)
                    self.assertEqual(z["selected"],4*(s*s-n)<=s)

if __name__=="__main__":
    unittest.main(verbosity=2)

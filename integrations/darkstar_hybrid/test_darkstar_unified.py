#!/usr/bin/env python3
"""Regression tests for the unified synthetic-only Dark Star pipeline. ZERO QPU."""
import math
import random
import unittest

from integrations.darkstar_hybrid import darkstar_unified as u
from simulation.ptp_hybrid import core
from hardware import dark_star_recycled_scalable_arithmetic_audit as gates


class UnifiedDarkStarTests(unittest.TestCase):
    def test_periodic_roots_and_kernel_table(self):
        self.assertEqual(len(core.ROOTS), 48)
        table=core.factor_pair_table()
        self.assertEqual(len(table), 48)
        self.assertEqual(set(len(v) for v in table.values()),{24,28})
        for p,q in ((11,19),(23,31),(11,71),(59,61)):
            n=p*q
            meta=u.ptp_public_metadata(n)
            self.assertFalse(meta["naive_diagonal_symmetry_pruning_enabled"])
            self.assertIn(meta["candidate_kernel_pairs"],(24,28))
            self.assertTrue(u.ptp_validate_recovered(n,[p,q]))
        self.assertFalse(u.ptp_validate_recovered(209,[7,29]))

    def test_public_cf_exact_and_no_private_inputs(self):
        # 2 has order 4 mod 15: y/Q=1/4 yields verified 3*5.
        z=u.online_public_cf(15,2,8,64)
        self.assertEqual(z["factors"],[3,5])
        self.assertTrue(z["ptp_validated"])
        self.assertGreater(z["ledger"]["modular_pow_calls"],0)
        self.assertGreater(z["ledger"]["gcd_calls"],0)
        self.assertIsNone(u.online_public_cf(15,2,8,0)["factors"])
        self.assertEqual(list(u.online_public_cf.__code__.co_varnames[:4]),["n","base","m","y"])

    def test_exact_odd_power_validation(self):
        for p,q,a in ((11,19,3),(23,31,19),(11,71,29),(5,7,2)):
            n=p*q
            r=gates.multiplicative_order_from_lambda(a,n,math.lcm(p-1,q-1))
            for e in u.ODD_EXPONENTS:
                b=pow(a,e,n)
                self.assertEqual(gates.multiplicative_order_from_lambda(b,n,math.lcm(p-1,q-1)),
                                 r//math.gcd(r,e))
                if r%2==0:
                    reduced=r//math.gcd(r,e)
                    self.assertEqual(pow(a,r//2,n),pow(b,reduced//2,n))

    def test_qpe_head_normalization_and_tail_honesty(self):
        for m in (4,6,8,12,16):
            rng=random.Random(8776)
            for _ in range(30):
                z=u.ideal_head_measurement(90,m,rng)
                self.assertGreaterEqual(z["head_mass"],0.)
                self.assertLessEqual(z["head_mass"],1.+1e-8)
                self.assertEqual(z["evaluated_bins"],min(65,1<<m))
                self.assertLessEqual(z["theoretical_tail_mass"],1./63+1e-6)
                if z["unmodeled_tail_event"]:
                    self.assertIsNone(z["y"])
                else:
                    self.assertGreaterEqual(z["y"],0)
                    self.assertLess(z["y"],1<<m)

    def test_classical_method_controls(self):
        for n,a in ((209,3),(713,19),(781,29),(35,2)):
            classical=u.public_classical_preflight(n,a)
            baseline=u.classical_reference_benchmarks(n)
            self.assertTrue(classical["classically_solved"])
            for name in ("trial","conventional_wheel210","ptp_LFK_kernel"):
                self.assertIsNotNone(baseline[name]["factors"],(n,name))
                self.assertEqual(math.prod(baseline[name]["factors"]),n)

    def test_whole_pipeline_and_no_false_hardware_gain(self):
        for p,q,a in ((11,19,3),(23,31,19),(5,7,2)):
            r=u.run_synthetic_case(p,q,a,seed=8776,fermat_tests=12)
            self.assertTrue(r["actual_classical_first_outcome"]["success"])
            self.assertEqual(r["actual_classical_first_outcome"]["factors"],[p,q])
            self.assertFalse(r["actual_classical_first_outcome"]["truly_requires_quantum_after_public_preflight"])
            self.assertEqual(len(r["all_fixed_exponent_ablation_arms"]),7)
            self.assertEqual(r["public_conditional_odd_exponent"],3 if r["N"]%3==2 else 1)
            self.assertFalse(r["public_PTPTables"]["naive_diagonal_symmetry_pruning_enabled"])
            self.assertTrue(r["safety"]["did_not_use_hidden_factors_for_public_decisions"])
            self.assertEqual(r["safety"]["IBM_runtime_jobs"],0)
            self.assertFalse(r["safety"]["uses_QPU"])
            arms=r["all_fixed_exponent_ablation_arms"]
            for label,z in arms.items():
                if z["model_attempted"]:
                    self.assertEqual(math.prod(z["factors"]) if z["factors"] else 0,
                                     r["N"] if z["success"] else 0)
                    width=z["logical_architectures"]
                    self.assertLess(width["recycled_peak_logical"],width["wide_peak_logical"])
                    self.assertEqual(z["validation_only_order"],
                                     z["validation_only_original_order"]//
                                     math.gcd(z["validation_only_original_order"],z["exponent"]))
                    self.assertEqual(z["counterfactual_source_counts"]["shots"],
                                     sum(s["shots_attempted"] for s in z["stage_receipts"]))
            four=r["four_way_comparison"]
            for first,second in (("standard_plain_wide","standard_plain_recycled"),
                                 ("PTP_conditional_wide","PTP_conditional_recycled")):
                if "source_CCX" in four[first]:
                    self.assertEqual(four[first]["source_CCX"],four[second]["source_CCX"])
                    self.assertLess(four[second]["peak_logical_qubits"],
                                    four[first]["peak_logical_qubits"])

    def test_exponent_selector_public_only(self):
        self.assertEqual(u.public_base(209,3),3)
        self.assertEqual(u.public_base(713,19),19)
        self.assertEqual(u.proper_factor_public(35,8)["factors"],[5,7])
        with self.assertRaises(ValueError):
            u.run_synthetic_case(11,11,3)
        with self.assertRaises(ValueError):
            u.run_synthetic_case(11,21,3)


if __name__=="__main__":
    unittest.main(verbosity=2)

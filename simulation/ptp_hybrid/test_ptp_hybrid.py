#!/usr/bin/env python3
from __future__ import annotations

import math
import unittest

try:
    from .core import (
        MODULUS,
        ROOTS,
        candidate_factor_pairs,
        exhaustive_core_report,
        factor_pair_table,
        is_ptp_candidate,
        primes_in_range,
        ptp_coordinate,
        root_for_integer,
        root_index,
    )
    from .kernel import lfk_factor, verify_actual_pair_present, wheel210_factor
    from .symmetry import audit_diagonal_canonicalization, table_symmetry_report
except ImportError:
    from core import (  # type: ignore
        MODULUS,
        ROOTS,
        candidate_factor_pairs,
        exhaustive_core_report,
        factor_pair_table,
        is_ptp_candidate,
        primes_in_range,
        ptp_coordinate,
        root_for_integer,
        root_index,
    )
    from kernel import lfk_factor, verify_actual_pair_present, wheel210_factor  # type: ignore
    from symmetry import audit_diagonal_canonicalization, table_symmetry_report  # type: ignore


class TestPTPCore(unittest.TestCase):
    def test_root_generation(self):
        self.assertEqual(MODULUS, 210)
        self.assertEqual(len(ROOTS), 48)
        self.assertEqual(ROOTS[0], 11)
        self.assertEqual(ROOTS[-1], 211)
        self.assertTrue(all(math.gcd(r, 210) == 1 for r in ROOTS))

    def test_coordinates_roundtrip(self):
        for n in range(11, 20_000):
            if not is_ptp_candidate(n):
                continue
            r, k = ptp_coordinate(n)
            self.assertEqual(n, r + 210 * k)
            self.assertEqual(root_for_integer(n), r)
            self.assertEqual(ROOTS[root_index(n) - 1], r)

    def test_every_prime_gt7_is_in_root_set(self):
        for p in primes_in_range(50_000, 11):
            self.assertTrue(is_ptp_candidate(p))
            self.assertIn(root_for_integer(p), ROOTS)

    def test_factor_pair_counts_24_or_28(self):
        table = factor_pair_table()
        counts = [len(v) for v in table.values()]
        self.assertEqual(counts.count(24), 42)
        self.assertEqual(counts.count(28), 6)
        for target, pairs in table.items():
            self.assertTrue(all((a * b - target) % 210 == 0 for a, b in pairs))

    def test_28_rows_have_eight_self_pairs(self):
        table = factor_pair_table()
        rows = [pairs for pairs in table.values() if len(pairs) == 28]
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(sum(a == b for a, b in pairs) == 8 for pairs in rows))

    def test_core_report(self):
        self.assertTrue(exhaustive_core_report(20_000)["pass"])


class TestKernelFactorSearch(unittest.TestCase):
    CASES = [15, 21, 33, 35, 39, 51, 55, 65, 77, 85, 91, 143, 187, 221, 323, 437, 899]

    def test_lfk_and_wheel_agree(self):
        for n in self.CASES:
            lfk = lfk_factor(n)
            wheel = wheel210_factor(n)
            self.assertIsNotNone(lfk.factors, n)
            self.assertEqual(lfk.factors, wheel.factors, n)
            p, q = lfk.factors
            self.assertEqual(p * q, n)
            self.assertTrue(verify_actual_pair_present(p, q))

    def test_actual_root_pairs_present_for_prime_pairs(self):
        primes = list(primes_in_range(500, 11))
        for i, p in enumerate(primes):
            for q in primes[i:]:
                self.assertTrue(verify_actual_pair_present(p, q), (p, q))


class TestSymmetryFalsification(unittest.TestCase):
    def test_residue_table_is_diagonal_mirror_closed(self):
        report = table_symmetry_report()
        self.assertTrue(report["all_rows_closed"])

    def test_diagonal_canonicalization_is_not_assumed_safe(self):
        audit = audit_diagonal_canonicalization(300)
        self.assertFalse(audit.safe_for_fixed_n_factor_search)
        self.assertIsNotNone(audit.first_counterexample)
        self.assertTrue(audit.first_counterexample["actual_pair_would_be_dropped"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

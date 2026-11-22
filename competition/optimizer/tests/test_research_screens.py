from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from competition.optimizer.autonomous.arithmetic import emit_terms, oracle_form
from competition.optimizer.autonomous.core import cost, parse, prove
from competition.optimizer.research.quadratic_span import resynthesize, scan
from competition.optimizer.research.scratch_liveness import width_screen


class ResearchScreenTests(unittest.TestCase):
    def test_width_releases_exactly_uncomputed_dirty_control_product(self):
        circuit = (
            "APPEND_TO_REGISTER q0 r0\nAPPEND_TO_REGISTER q1 r0\n"
            "CCX q0 q1 q2\nZ q2\nCCX q0 q1 q2\nX q3\n"
        )
        report = width_screen(circuit)
        self.assertEqual(report["fixed_order_hmr_peak"], 4)
        self.assertEqual(report["fixed_order_symbolic_peak"], 3)
        self.assertEqual(report["wires_with_other_zero_release"], [2])

    def test_width_guard_is_captured_even_when_bit_is_overwritten(self):
        circuit = (
            "PUSH_CONDITION if b0\nX q0\nBIT_STORE0 b0\nX q0\n"
            "POP_CONDITION\nX q1\n"
        )
        self.assertEqual(width_screen(circuit)["fixed_order_symbolic_peak"], 1)
        self.assertEqual(width_screen(circuit.replace("X q0\nPOP", "X q0 if b0\nPOP"))[
            "fixed_order_symbolic_peak"], 2)

    def test_width_does_not_release_scratch_after_conditional_measurement(self):
        circuit = "X q0\nHMR q0 b1 if b0\nX q1\n"
        self.assertEqual(width_screen(circuit)["fixed_order_symbolic_peak"], 2)
        self.assertEqual(width_screen(circuit.replace(" if b0", ""))[
            "fixed_order_symbolic_peak"], 1)

    def test_width_rejects_unsupported_operations_and_unmatched_pop(self):
        for line in ("H q2", "POP_CONDITION"):
            with self.subTest(line=line), self.assertRaises(ValueError):
                width_screen(line)

    def test_quadratic_span_saves_one_toffoli_beyond_shared_monomials(self):
        # Each destination is independently dirty. Existing monomial sharing
        # needs three nonlinear products. The three outputs span two parities.
        a = "CCX q0 q1 q4\nCCX q0 q2 q4\n"
        b = "CCX q0 q1 q5\nCCX q0 q3 q5\n"
        c = "CCX q0 q2 q6\nCCX q0 q3 q6\n"
        gates = [parse(line) for line in (a + b + c).splitlines()]
        wires, terms, _, _ = oracle_form(gates)
        self.assertEqual(cost(emit_terms(wires, terms))[0], 3)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.kmx"
            path.write_text(a + b + c, encoding="utf-8")
            first = scan(path, 100, 16)["exact_local_findings"][0]
        self.assertEqual(first["before"][0], 6)
        self.assertEqual(first["after"][0], 2)
        self.assertEqual(first["proof"]["basis_states"], 128)
        self.assertEqual(first["proof"]["status"], "EXACT")

    def test_quadratic_span_corrects_linear_terms_from_overlapping_factors(self):
        gates = [parse(line) for line in (
            "CCX q0 q1 q3", "CCX q0 q2 q3", "CCX q1 q2 q3",
            "CCX q0 q1 q4", "CCX q0 q2 q4", "CCX q1 q2 q4", "CX q1 q4",
        )]
        after = resynthesize(oracle_form(gates), cost(gates)[0])
        self.assertEqual(cost(after)[0], 1)
        self.assertEqual(prove(gates, after)["status"], "EXACT")

    def test_quadratic_span_skips_rank_that_one_product_cannot_attain(self):
        gates = [parse(line) for line in ("CCX q0 q1 q4", "CCX q2 q3 q4", "CX q0 q5")]
        self.assertIsNone(resynthesize(oracle_form(gates), cost(gates)[0]))


if __name__ == "__main__":
    unittest.main()

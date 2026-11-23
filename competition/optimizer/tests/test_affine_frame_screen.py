import unittest

from competition.optimizer.autonomous.core import cost, parse, prove
from competition.optimizer.research.affine_frame_screen import optimize


def gates(source):
    return [gate for line in source.decode().splitlines() if (gate := parse(line))]


class AffineFrameTests(unittest.TestCase):
    def test_shares_product_between_two_output_forms(self):
        source = (
            b"CCX q0 q1 q6\nCX q8 q0\nCX q8 q0\n"
            b"CCX q2 q3 q6\nX q8\nCCX q0 q1 q7\nCCX q4 q5 q7\n"
        )
        candidate, report = optimize(source)
        self.assertIsNotNone(candidate)
        self.assertEqual(cost(gates(candidate))[0], 3)
        self.assertEqual(prove(gates(source), gates(candidate))["status"], "EXACT")
        self.assertEqual(report["selected_replacements"][0]["paid_gates_saved"], 1)

    def test_resynthesizes_controlled_swaps_through_a_parity_frame(self):
        source = b"CSWAP q0 q3 q4\nCX q2 q0\nCSWAP q0 q3 q4\n"
        candidate, _ = optimize(source)
        self.assertIsNotNone(candidate)
        self.assertEqual(cost(gates(candidate))[0], 1)
        self.assertEqual(prove(gates(source), gates(candidate))["status"], "EXACT")

    def test_keeps_measurements_and_conditions_as_barriers(self):
        source = b"CCX q0 q1 q3\nHMR q5 b2\nCCX q0 q2 q3\n"
        candidate, report = optimize(source)
        self.assertIsNone(candidate)
        self.assertEqual(report["tested_windows"], 0)
        source = b"CCX q0 q1 q3\nPUSH_CONDITION if b2\nCCX q0 q2 q3\nPOP_CONDITION\n"
        candidate, report = optimize(source)
        self.assertIsNone(candidate)
        self.assertEqual(report["tested_windows"], 0)


if __name__ == "__main__":
    unittest.main()

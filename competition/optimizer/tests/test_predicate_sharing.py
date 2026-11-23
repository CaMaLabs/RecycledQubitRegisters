import unittest
from competition.optimizer.autonomous.core import Gate, EIGHTH, prove
from competition.optimizer.autonomous.predicate_sharing import predicate_share


class PredicateSharingTests(unittest.TestCase):
    def test_shared_computed_predicate(self):
        a = [
            Gate("CCX", (0, 1, 2)),
            Gate("Z_POW", (2,), EIGHTH),
            Gate("CZ", (2, 3)),
            Gate("Z_POW", (2,), EIGHTH),
            Gate("CCX", (0, 1, 2)),
        ]
        proposal = predicate_share(a, {}, 0)
        self.assertIsNotNone(proposal)
        self.assertEqual(prove(a, proposal.gates)["status"], "EXACT")
        self.assertLess(len(proposal.gates), len(a))

    def test_noncommuting_gate_blocks(self):
        a = [
            Gate("Z_POW", (2,), EIGHTH),
            Gate("CX", (2, 3)),
            Gate("Z_POW", (2,), EIGHTH),
        ]
        self.assertIsNone(predicate_share(a, {}, 0))

    def test_opposite_rotations_cancel(self):
        a = [
            Gate("Z_POW", (0,), EIGHTH),
            Gate("CZ", (0, 1)),
            Gate("Z_POW", (0,), (-EIGHTH) % (1 << 128)),
        ]
        proposal = predicate_share(a, {}, 0)
        self.assertIsNotNone(proposal)
        self.assertEqual(prove(a, proposal.gates)["status"], "EXACT")


if __name__ == "__main__":
    unittest.main()

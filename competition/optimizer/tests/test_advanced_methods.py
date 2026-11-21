from itertools import combinations
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from competition.optimizer.autonomous.arithmetic import arithmetic_resynthesis, recycle_workspace
from competition.optimizer.autonomous.affine_synthesis import constrained_affine
from competition.optimizer.autonomous.controller import synthesis_key
from competition.optimizer.autonomous.core import EIGHTH, TURN, Gate, cost, parse, prove
from competition.optimizer.autonomous.phase_precision import (
    parity_network, phase_function, phase_predicate,
)

BUDGET = {"depth": 4, "max_states": 100000, "seconds": 5}


class AdvancedTests(unittest.TestCase):
    def exact(self, before, proposal, resource, expected):
        self.assertIsNotNone(proposal)
        self.assertEqual(prove(before, proposal.gates)["status"], "EXACT")
        self.assertEqual(cost(proposal.gates)[resource], expected)
        self.assertLess(cost(proposal.gates), cost(before))

    def test_arithmetic_full_adder_carry_has_alternative_one_toffoli_architecture(self):
        gates = [Gate("CCX", (*pair, 3)) for pair in combinations(range(3), 2)]
        result = arithmetic_resynthesis(gates, BUDGET, 1)
        self.assertEqual(result.detail["arithmetic_family"], "full_adder_carry")
        self.exact(gates, result, 0, 1)

    def test_in_place_add_subtract_and_out_of_place_multiply(self):
        add = [Gate("CCX", (0, 2, 3)), Gate("CX", (1, 3)), Gate("CX", (0, 2))]
        redundant = [Gate("CCX", (0, 2, 3))] * 2
        for before, name in [(add, "in_place_add_2"), (add[::-1], "in_place_subtract_2")]:
            gates = redundant + before
            result = arithmetic_resynthesis(gates, BUDGET, 1)
            self.assertEqual(result.detail["arithmetic_family"], name)
            self.exact(gates, result, 0, 1)
        gates = [Gate("CCX", (0, 1, 2))] * 3
        result = arithmetic_resynthesis(gates, BUDGET, 1)
        self.assertEqual(result.detail["arithmetic_family"], "multiply_low_word")
        self.exact(gates, result, 0, 1)

    def test_unsigned_comparator_truth_table(self):
        compare = [Gate("CX", (1, 2)), Gate("CCX", (0, 1, 2))]
        gates = compare + [Gate("CCX", (0, 1, 2))] * 2
        result = arithmetic_resynthesis(gates, BUDGET, 1)
        self.assertEqual(result.detail["arithmetic_family"], "unsigned_less_than")
        self.exact(gates, result, 0, 1)

    def test_workspace_reuse_preserves_dirty_helper(self):
        compute = Gate("CCX", (0, 1, 2))
        gates = [compute, Gate("CX", (2, 3)), compute]
        result = recycle_workspace(gates, BUDGET, 1)
        self.assertIn(Gate("CX", (2, 3)), result.gates)
        self.exact(gates, result, 0, 1)

    def test_workspace_fanout_across_disjoint_operations(self):
        compute = Gate("CCX", (0, 1, 2))
        gates = [compute, Gate("CX", (2, 3)), Gate("X", (5,)),
                 Gate("CX", (2, 4)), compute]
        result = recycle_workspace(gates, BUDGET, 1)
        self.exact(gates, result, 0, 1)
        self.assertEqual(result.detail["fanout"], 2)
        gates[2] = Gate("CX", (5, 4))
        self.assertIsNone(recycle_workspace(gates, BUDGET, 1))

    def test_kickmix_rounding_and_unmodified_serialization(self):
        self.assertEqual(parse("Z_POW q0 0.25").angle, EIGHTH)
        self.assertEqual(parse("Z_POW q0 -0.25").angle, TURN - EIGHTH)
        self.assertEqual(parse("Z_POW q0 2.0").angle, 0)
        for ticks in [0, 1, 3, EIGHTH, TURN - 1]:
            gate = Gate("Z_POW", (0,), ticks)
            self.assertEqual(parse(gate.text()), gate)

    def test_kickmix_half_tick_ties_round_to_even(self):
        first = f"0.{5**128:0128d}"
        second = f"0.{3 * 5**128:0128d}"
        self.assertEqual(parse(f"Z_POW q0 {first}").angle, 0)
        self.assertEqual(parse(f"Z_POW q0 {second}").angle, 2)
        # The exact proof rejects a missing branch-dependent rotation.
        self.assertEqual(prove([parse("Z_POW q0 0.1")], [])["status"], "REJECTED")

    def test_verifier_queue_reopens_timeout_and_excludes_finished_pass(self):
        from competition.optimizer.autonomous.store import Store

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "queue.db"
            store = Store(db)
            store.candidate("first", None, "a.kmx", {})
            store.candidate("second", None, "b.kmx", {})
            store.queue_verification("first", 20)
            store.queue_verification("second", 10)
            store.receipt("first", {"status": "TIMEOUT"})
            store.receipt("second", {"status": "PASS_FULL", "score": 123})
            store.close()
            reopened = Store(db)
            self.assertEqual([r["sha"] for r in reopened.pending_verifications()], ["first"])
            reopened.close()

    def test_phase_fold_merges_arbitrary_fixed_precision_rotations(self):
        for first, second in [("0.1", "0.2"), ("0.00000762939589250735", "0.3")]:
            gates = [parse(f"Z_POW q0 {first}"), Gate("CX", (0, 1)),
                     parse(f"Z_POW q0 {second}")]
            self.exact(gates, phase_function(gates, BUDGET, 1), 1, 1)

    def test_nonlinear_phase_predicate(self):
        compute = Gate("CCX", (0, 1, 2))
        a = parse("Z_POW q2 0.1")
        b = parse("Z_POW q2 0.2")
        gates = [compute, a, compute, Gate("X", (3,)), compute, b, compute]
        self.exact(gates, phase_predicate(gates, BUDGET, 1), 1, 1)
        self.assertIsNone(phase_predicate([a, compute, b], BUDGET, 1))

    def test_rank_four_walsh_identity(self):
        gates = []
        wires = list(range(4))
        for mask in range(1, 16):
            pivot = mask.bit_length() - 1
            basis = parity_network(mask, wires, pivot)
            gates.extend(basis + [Gate("T", (pivot,))] + basis[::-1])
        result = phase_function(gates, BUDGET, 1)
        self.assertEqual(result.detail["method"], "walsh_rank_four_null_relation")
        self.exact(gates, result, 1, 0)

    @unittest.skipUnless(importlib.util.find_spec("z3"), "Optional Z3 not installed")
    def test_affine_smt_sat_and_scoped_unsat(self):
        gates = [Gate("CCX", (*pair, 4)) for pair in [(0, 2), (0, 3), (1, 2), (1, 3)]]
        result = constrained_affine(gates, BUDGET, 1)
        self.assertEqual(result.detail["solver_status"], "SAT")
        self.exact(gates, result, 0, 1)
        independent = [Gate("CCX", (0, 1, 4)), Gate("CCX", (2, 3, 4))]
        result = constrained_affine(independent, BUDGET, 1)
        self.assertEqual(result.detail["solver_status"], "UNSAT")

    def test_semantic_cache_key_matches_distinct_equivalent_programs(self):
        a = Gate("CCX", (0, 1, 4))
        b = Gate("CCX", (2, 3, 4))
        self.assertEqual(synthesis_key([a, b], BUDGET, 1)[0],
                         synthesis_key([b, a], BUDGET, 1)[0])
        self.assertNotEqual(synthesis_key([a, b], BUDGET, 1)[0],
                            synthesis_key([b, a], {**BUDGET, "depth": 1}, 1)[0])

    def test_end_to_end_new_plugins_and_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "arith-phase.kmx"
            source.write_text("CCX q0 q1 q3\nCCX q0 q2 q3\nCCX q1 q2 q3\n"
                              "HMR q4 b0\nZ_POW q0 0.1\nCX q0 q1\nZ_POW q0 0.2\n")
            config = root / "config.json"
            config.write_text(json.dumps({"methods":["arithmetic","phase_function"],
                                          "levels":1,"max_jobs":12,"concurrency":2}))
            out = root / "run"
            result = subprocess.run([sys.executable, "competition/optimizer/run_autonomous.py",
                "--source", str(source), "--out", str(out), "--config", str(config)],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["census"]["source_opcodes"]["CCX"], 1)
            self.assertEqual(summary["census"]["source_opcodes"]["Z_POW"], 1)
            self.assertTrue((out / "experiments.sqlite3").is_file())
            self.assertEqual(summary["experiment_counts"]["COMPOSED"], 1)
            from competition.optimizer.replay_candidate import replay
            check = replay(out / "experiments.sqlite3", source,
                           summary["current_exact_candidate"], root / "replayed.kmx")
            self.assertEqual(check["exact_steps"], 2)
            self.assertIsNone(summary["best_official"])

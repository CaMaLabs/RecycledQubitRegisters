import itertools
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from competition.optimizer.autonomous.core import sha
from competition.optimizer.autonomous.kickmix_trace import load_program
from competition.optimizer.autonomous.qrom_products import optimize
from competition.optimizer.replay_candidate import replay


HEADER = "".join(f"APPEND_TO_REGISTER q{i} r0\n" for i in range(6)) + "REGISTER r0 \"x\"\n"
MIXED = HEADER + "R q6\nCCX q0 q1 q2\nCCZ q0 q1 q3\nCCX q0 q1 q4\n"


def scalar(circuit, value, outcome):
    """Independent basis-state and branch-phase reference for these fixtures."""
    program, pinned = load_program(circuit.decode())
    q = [value >> i & 1 if i in pinned else 0 for i in range(7)]
    bits, guards, phase, charged = {}, [], 0, 0
    for _, op, wires, bit, guard in program:
        if op == "PUSH_CONDITION":
            guards.append(bits.get(guard, 0))
            continue
        if op == "POP_CONDITION":
            guards.pop()
            continue
        if not all(guards) or (guard is not None and not bits.get(guard, 0)):
            continue
        charged += op in {"CCX", "CCZ"}
        if op in {"CCX", "CX", "X"}:
            q[wires[-1]] ^= int(all(q[i] for i in wires[:-1]))
        elif op in {"CCZ", "CZ", "Z"}:
            phase ^= int(all(q[i] for i in wires))
        elif op == "R":
            if q[wires[0]]:
                raise AssertionError("Reset fixture must be clean")
        elif op == "HMR":
            bits[bit] = outcome
            phase ^= q[wires[0]] & outcome
            q[wires[0]] = 0
        elif op in {"BIT_STORE0", "BIT_STORE1"}:
            bits[bit] = int(op == "BIT_STORE1")
        else:
            raise AssertionError(op)
    return (q, phase, bits), charged


class QromProductsTests(unittest.TestCase):
    def verify_fixture(self, circuit):
        before = circuit.encode()
        after, report = optimize(before)
        cost_before = cost_after = 0
        for value, outcome in itertools.product(range(64), range(2)):
            reference, before_charge = scalar(before, value, outcome)
            observed, after_charge = scalar(after, value, outcome)
            self.assertEqual(reference, observed, (value, outcome))
            cost_before += before_charge
            cost_after += after_charge
        return after, report, (cost_before - cost_after) / 128

    def test_joint_bank_mixes_decoder_writes_with_phase_cleanup(self):
        after, report, saving = self.verify_fixture(MIXED)
        self.assertEqual(saving, 1)
        self.assertEqual(len(report["banks"]), 1)
        self.assertEqual(report["banks"][0]["replaced_lines"], [9, 10, 11])
        self.assertIn(b"CZ q6 q3", after)

    def test_guarded_bank_charges_two_paid_gates_and_counts_dependent_guard_once(self):
        body = ("PUSH_CONDITION if b0\nPUSH_CONDITION if b0\n"
                "CCX q0 q1 q2\nCCZ q0 q1 q3\nCCX q0 q1 q4\n"
                "CCZ q0 q1 q5\nCCZ q0 q1 q2\nPOP_CONDITION\nPOP_CONDITION\n")
        source = HEADER + "HMR q6 b0\n" + body
        _, report, saving = self.verify_fixture(source)
        self.assertEqual(saving, 0.5)
        self.assertEqual(report["banks"][0]["net_expected_toffoli_saving_lower_bound"], "1/2")
        four = source.replace("CCZ q0 q1 q5\n", "")
        self.assertEqual(optimize(four.encode())[1]["banks"], [])
        writes_control = source.replace("CCX q0 q1 q2\n", "X q0\nCCX q0 q1 q2\n")
        self.assertEqual(optimize(writes_control.encode())[1]["banks"], [])

    def test_parity_of_existing_dirty_wires_can_replace_a_product(self):
        circuit = HEADER + "CX q2 q6\nCCX q0 q1 q2\nCCZ q0 q1 q3\n"
        after, report, saving = self.verify_fixture(circuit)
        self.assertEqual(saving, 1)
        self.assertEqual(report["edits"][0]["witness"], "affine_live_products")
        self.assertIn(b"CZ q2 q3", after)
        self.assertIn(b"CZ q6 q3", after)

    def test_conditional_hmr_cannot_establish_unconditional_clean_bank(self):
        body = MIXED.removeprefix(HEADER + "R q6\n")
        source = HEADER + "X q6\nHMR q6 b1 if b0\n" + body
        self.assertEqual(optimize(source.encode())[1]["banks"], [])

    def test_physical_line_offsets_ignore_unicode_separators_in_comments(self):
        comment = "# separator \u2028 CCX q9 q8 q7\n"
        after, report, saving = self.verify_fixture(comment + MIXED)
        self.assertTrue(after.startswith(comment.encode()))
        self.assertEqual(report["banks"][0]["replaced_lines"], [10, 11, 12])
        self.assertEqual(saving, 1)

    def test_campaign_archives_result_and_replays_from_source(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, out = root / "input.kmx", root / "run"
            source.write_text(MIXED)
            args = [sys.executable, "competition/optimizer/run_autonomous.py",
                    "--source", str(source), "--out", str(out), "--qrom-products-only", "--resume"]
            result = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["experiment_counts"], {"LOCAL_IMPROVEMENT": 1})
            self.assertIsNone(summary["best_official"])
            current = summary["current_exact_candidate"]
            check = replay(out / "experiments.sqlite3", source, current, root / "replayed.kmx")
            self.assertEqual(check["exact_steps"], 1)
            self.assertEqual((root / "replayed.kmx").read_bytes(), (out / (current + ".kmx")).read_bytes())
            resumed = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
            self.assertEqual(json.loads((out / "summary.json").read_text())["current_exact_candidate"], current)

    def test_campaign_promotion_uses_the_shared_full_verifier_pipeline(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, out = root / "input.kmx", root / "run"
            source.write_text(MIXED)
            verifier = root / "mock.py"
            verifier.write_text(
                "import json, sys\nfrom pathlib import Path\n"
                "ops = Path(sys.argv[1]).read_text().splitlines()\n"
                "score = sum(line.startswith(('CCX ', 'CCZ ')) for line in ops)\n"
                "print(json.dumps(dict(status='PASS', score=score, verified_shots=64)))\n"
            )
            contract = root / "contract.json"
            contract.write_text(json.dumps({"script": str(verifier), "script_sha256": sha(verifier.read_bytes()),
                "direction": "minimize", "seeds": [7, 17], "full_shots": 64,
                "fields": {"cost": "score"}, "argv": ["{python}", "{script}", "{candidate}"]}))
            result = subprocess.run([sys.executable, "competition/optimizer/run_autonomous.py",
                "--source", str(source), "--out", str(out), "--qrom-products-only", "--contract", str(contract)],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["measured_baseline_score"], 3)
            self.assertEqual(summary["best_official"]["score"], 2)
            self.assertTrue(summary["success"])
            receipt_path = out / "verify" / summary["best_official"]["sha"] / "receipt.json"
            receipts = json.loads(receipt_path.read_text())["runs"]
            self.assertEqual([item["status"] for item in receipts], ["PASS_FULL", "PASS_FULL"])


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from competition.optimizer.autonomous.conditional import (
    conditional_phase, parse_region, render_region,
)
from competition.optimizer.autonomous.controller import regions
from competition.optimizer.autonomous.core import cost, prove, sha
from competition.optimizer.replay_candidate import replay


class ConditionalTests(unittest.TestCase):
    def test_shared_guard_ccz_rewrite_preserves_exact_phase(self):
        lines = ["CCZ q0 q1 q2 if b8", "CCZ q0 q1 q3 if b8"]
        before = parse_region(lines, "b8")
        candidate = conditional_phase(before, {}, 0)
        self.assertEqual(cost(candidate.gates)[0], 1)
        self.assertEqual(prove(before, candidate.gates)["status"], "EXACT")
        self.assertEqual(render_region(candidate.gates, "b8"), [
            "CX q3 q2 if b8\n", "CCZ q0 q1 q2 if b8\n", "CX q3 q2 if b8\n",
        ])

    def test_different_bits_and_writes_split_the_region(self):
        lines = ["CCZ q0 q1 q2 if b8", "CCZ q0 q1 q3 if b9",
                 "BIT_INVERT b9", "CCZ q0 q1 q2 if b9", "CZ q1 q2 if b9"]
        found = regions(lines, {"wires": 4, "span": 12}, "conditional_phase", 10)
        self.assertEqual([(a,b,guard) for a,b,_,guard in found], [(3,5,"b9")])


class CheckpointTests(unittest.TestCase):
    def run_optimizer(self, command):
        result = subprocess.run(command, capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_free_checkpoint_verifies_and_can_be_replayed_and_selected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "source.kmx"
            source.write_text("HMR q4 b8\nCZ q0 q1 if b8\nCZ q0 q1 if b8\n")
            config = folder / "config.json"
            config.write_text(json.dumps({"methods":["conditional_phase"],"levels":1}))
            script = folder / "mock.py"
            script.write_text('print(\'{"status":"PASS","score":9,"verified_shots":5,"count":1}\')\n')
            contract = folder / "contract.json"
            contract.write_text(json.dumps({"script":str(script),
                "script_sha256":sha(script.read_bytes()), "direction":"minimize",
                "seeds":[12345],"full_shots":5,"fields":{"count":"count"},
                "argv":["{python}","{script}","{candidate}"]}))
            out = folder / "run"
            command = [sys.executable,"competition/optimizer/run_autonomous.py",
                       "--source",str(source),"--out",str(out),"--config",str(config)]
            self.run_optimizer(command + ["--contract",str(contract)])
            summary = json.loads((out/"summary.json").read_text())
            candidate = summary["current_exact_candidate"]
            database = out/"experiments.sqlite3"
            receipt = json.loads((out/"verify"/candidate/"receipt.json").read_text())
            self.assertEqual(receipt["runs"][0]["status"], "PASS_FULL")
            self.assertEqual(summary["best_official"]["sha"], sha(source.read_bytes()))
            self.assertFalse(summary["success"])
            replay(database, source, candidate, folder/"replay.kmx")
            self.assertEqual((folder/"replay.kmx").read_text(), "HMR q4 b8\n")
            (out/(candidate+".kmx")).unlink()
            self.run_optimizer(command + ["--resume","--start-from",candidate])
            summary = json.loads((out/"summary.json").read_text())
            self.assertEqual(summary["started_from"],candidate)
            self.assertEqual(summary["measured_baseline_score"],9)
            self.assertEqual(summary["archived_candidate_count"],2)
            self.assertEqual((out/(candidate+".kmx")).read_text(), "HMR q4 b8\n")

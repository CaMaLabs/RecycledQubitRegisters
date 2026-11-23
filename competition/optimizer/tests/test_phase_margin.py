import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


@unittest.skipUnless(importlib.util.find_spec("numpy") and importlib.util.find_spec("scipy"),
                     "Optional phase fitting dependencies unavailable")
class PhaseMarginTests(unittest.TestCase):
    def test_joint_fit_increases_exhaustive_integer_margin(self):
        import numpy as np
        from competition.optimizer.autonomous.phase_margin import angle_shift, fit_phase

        mask = np.array([0, 1, 2, 3], dtype=np.uint64)
        residual = np.array([10, 30, -30, -10], dtype=np.int64)
        tolerance = np.full(4, 100, dtype=np.int64)
        fit = fit_phase(mask, residual, tolerance, 2)
        measured = min(tolerance - np.abs(residual + angle_shift(mask, fit.delta)))
        self.assertEqual(fit.margin, measured)
        self.assertEqual(fit.margin, 90)
        self.assertTrue(fit.converged)

    def test_fixed_offset_survives_rounding_and_impossible_drop_is_reported(self):
        import numpy as np
        from competition.optimizer.autonomous.phase_margin import fit_phase

        mask = np.array([0, 1], dtype=np.uint64)
        residual = np.array([0, 0], dtype=np.int64)
        tolerance = np.full(2, 10, dtype=np.int64)
        fit = fit_phase(mask, residual, tolerance, 1, {0: -15})
        self.assertEqual(fit.delta, (-15,))
        self.assertEqual(fit.margin, -5)

    def test_extra_rotation_can_cost_more_even_with_better_margin(self):
        from competition.optimizer.autonomous.phase_margin import rotation_price

        self.assertGreater(rotation_price(42, 63_755_774), rotation_price(41, 58_597_850))

    def test_candidate_requires_matching_fully_verified_campaign(self):
        from competition.optimizer.autonomous.core import sha
        from competition.optimizer.autonomous.store import Store
        from competition.optimizer.autonomous.verification import verify
        from competition.optimizer.research.invsqrt_phase_fit import verify_against_campaign

        with TemporaryDirectory() as folder:
            work = Path(folder)
            script = work / "mock.py"
            script.write_text(
                "import json, sys\n"
                "from pathlib import Path\n"
                "score = len(Path(sys.argv[1]).read_text())\n"
                "print(json.dumps(dict(status='PASS', score=score, verified_shots=64)))\n"
            )
            source, candidate = work / "source.kmx", work / "candidate.kmx"
            source.write_bytes(b"abc")
            candidate.write_bytes(b"a")
            source_hash, candidate_hash = sha(source.read_bytes()), sha(candidate.read_bytes())
            contract = {"script": str(script), "script_sha256": sha(script.read_bytes()),
                        "direction": "minimize", "full_shots": 64, "seeds": [7, 17],
                        "fields": {"cost": "score"},
                        "argv": ["{python}", "{script}", "{candidate}", "{workers}"]}
            database = work / "experiments.sqlite3"
            store = Store(database)
            full = verify(source, work / "base", contract, 10, 1024, 1, 20)
            store.set("identity", {"source_sha256": source_hash, "contract": contract, "reference": 2})
            store.set("best", {"sha": source_hash, "score": full["score"]})
            store.candidate(source_hash, None, source, {"status": "SOURCE"})
            store.receipt(source_hash, full)
            store.close()
            report = {"source_sha256": "wrong", "candidate": {"sha256": candidate_hash}}
            with self.assertRaises(ValueError):
                verify_against_campaign(candidate, report, database, work, 10)
            report["source_sha256"] = source_hash
            verify_against_campaign(candidate, report, database, work, 10)
            self.assertEqual(report["official_status"], "PASS_FULL")
            self.assertTrue(report["verified_improvement"])
            self.assertTrue(report["beats_historical_reference"])
            verified = report["official_verifier_result"]["runs"]
            self.assertEqual([item["argv"][-1] for item in verified], ["1", "1"])


if __name__ == "__main__":
    unittest.main()

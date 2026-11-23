import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from competition.optimizer.autonomous.core import Gate, cost, prove
from competition.optimizer.autonomous.structured import identity_screen, parity_spectrum

BUDGET = {"seconds": 2, "max_states": 200}


class TransferTests(unittest.TestCase):
    def test_identity_screen_requires_both_permutation_and_phase_identity(self):
        block = [Gate("CX", (0, 1)), Gate("X", (0,)),
                 Gate("CX", (0, 1)), Gate("X", (0,)), Gate("X", (1,))]
        identity = identity_screen(block, BUDGET, 42)
        self.assertEqual(identity.gates, [])
        self.assertEqual(prove(block, identity.gates)["status"], "EXACT")
        block.append(Gate("T", (0,)))
        proposal = identity_screen(block, BUDGET, 42)
        self.assertEqual(proposal.gates, [Gate("T", (0,))])

    def test_spectral_phase_tracks_parity_across_wire_swaps(self):
        gates = [Gate("CX", (0, 1)), Gate("T", (1,)),
                 Gate("SWAP", (1, 2)), Gate("T", (2,)), Gate("CZ", (0, 2))]
        proposal = parity_spectrum(gates, BUDGET, 42)
        self.assertEqual(cost(proposal.gates)[1], 0)
        self.assertEqual(prove(gates, proposal.gates)["status"], "EXACT")
        flipped = [Gate("T", (0,)), Gate("X", (0,)), Gate("T_DAG", (0,))]
        self.assertIsNone(parity_spectrum(flipped, BUDGET, 42))


@unittest.skipUnless(importlib.util.find_spec("qiskit"), "Optional Qiskit not installed")
class CircuitIOTests(unittest.TestCase):
    def cli(self, source, out, *extra):
        cmd = [sys.executable, "competition/optimizer/run_autonomous.py", "--source", str(source),
               "--out", str(out), "--max-jobs", "36", *extra]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((out / "summary.json").read_text())

    def test_qpy_bundle_preserves_opaque_control_and_symbolic_state_on_resume(self):
        from qiskit import QuantumCircuit, qpy
        from qiskit.circuit import Parameter
        from qiskit.circuit.library import CXGate, SGate

        circuit = QuantumCircuit(3, 1, metadata={"test": "roundtrip"}, global_phase=0.125)
        circuit.h(0)
        circuit.t(1)
        circuit.swap(1, 2)
        circuit.t(2)
        circuit.rx(Parameter("theta"), 1)
        circuit.append(CXGate(ctrl_state=0), [0, 1])
        circuit.measure(0, 0)
        with circuit.if_test((circuit.clbits[0], True)):
            circuit.x(2)
        circuit.reset(0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "bundle.qpy"
            with source.open("wb") as stream:
                qpy.dump([QuantumCircuit(1), circuit], stream)
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            info = self.cli(source, root / "run", "--circuit-index", "1")
            self.assertEqual(info["original_source_sha256"], before)
            self.assertEqual(info["output_metrics"]["operation_counts"].get("t", 0), 0)
            with Path(info["output_circuit"]).open("rb") as stream:
                result, = qpy.load(stream)
            expected = circuit.copy()
            expected.data[1] = expected.data[1].replace(operation=SGate())
            del expected.data[3]
            self.assertEqual(result, expected)
            self.assertEqual(result.metadata, circuit.metadata)
            resumed = self.cli(source, root / "run", "--circuit-index", "1", "--resume")
            self.assertEqual(resumed["current_exact_candidate"], info["current_exact_candidate"])
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)

    def test_openqasm_2_and_3_roundtrip_unitaries(self):
        from qiskit import QuantumCircuit, qpy
        from qiskit.quantum_info import Operator
        for major, header, declarations in [
            (2, 'OPENQASM 2.0; include "qelib1.inc";', "qreg q[2];"),
            (3, 'OPENQASM 3.0; include "stdgates.inc";', "qubit[2] q;"),
        ]:
            with self.subTest(major=major), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "input.qasm"
                source.write_text(f"// example\n{header}\n{declarations}\nh q[0];\n"
                                  "t q[1];\nt q[1];\ncx q[0],q[1];\n")
                info = self.cli(source, root / "run")
                self.assertEqual(info["input_format"], f"qasm{major}")
                self.assertEqual(info["input_metrics"]["operations"], 4)
                self.assertEqual(info["output_metrics"]["operations"], 3)
                with Path(info["output_circuit"]).open("rb") as stream:
                    result, = qpy.load(stream)
                expected = QuantumCircuit(2)
                expected.h(0)
                expected.s(1)
                expected.cx(0, 1)
                self.assertTrue(Operator(result).equiv(Operator(expected)))

    def test_arbitrary_kmx_needs_no_k191_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.kmx"
            source.write_text("T q0\nT q0\n")
            info = self.cli(source, root / "run")
            self.assertIsNone(info["reference_score"])
            candidate = root / "run" / (info["current_exact_candidate"] + ".kmx")
            self.assertEqual(candidate.read_text(), "S q0\n")

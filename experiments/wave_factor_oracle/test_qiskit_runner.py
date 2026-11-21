"""Independent Aer checks of amplification, failure cases and QASM export."""
import tempfile
from pathlib import Path
import unittest

from qiskit import qasm2, transpile
from qiskit_aer import AerSimulator
import qiskit_runner as runner


class AerOracleTests(unittest.TestCase):
    def test_unamplified_distribution(self):
        result=runner.run(35,3,0,64,19)
        self.assertAlmostEqual(result['aer_success_probability'],0.25,places=8)

    def test_amplification_and_cleanup(self):
        result=runner.run(35,3,1,128,19)
        self.assertEqual(result['logical_qubits'],26)
        self.assertEqual(result['accepted_shots'],128)
        self.assertAlmostEqual(result['workspace_clean_mean_z'],1,places=8)
        self.assertLess(result['absolute_probability_error'],1e-8)

    def test_larger_quantum_divider(self):
        result=runner.run(323,5,3,128,19)
        self.assertEqual(result['logical_qubits'],38)
        self.assertAlmostEqual(result['aer_success_probability'],0.9613189697265625,places=8)
        self.assertEqual(result['accepted_shots']+result['rejected_shots'],128)
        self.assertTrue(set(result['measured_factor_pairs']).issubset({'17*19','19*17'}))

    def test_prime_has_no_accepted_branch(self):
        result=runner.run(331,5,3,64,19)
        self.assertAlmostEqual(result['aer_success_probability'],0,places=8)
        self.assertEqual(result['accepted_shots'],0)
        self.assertEqual(result['rejected_shots'],64)

    def test_qasm_roundtrip_executes(self):
        circuit,layout=runner.build_circuit(35,3,1,diagnostics=False)
        self.assertFalse(any(instruction.operation.name.startswith('save_')
                             for instruction in circuit.data))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'oracle.qasm'
            qasm2.dump(circuit,path)
            loaded=qasm2.load(path)
        self.assertEqual(loaded.num_qubits,layout.qubits)
        backend=AerSimulator(method='matrix_product_state',max_parallel_threads=2)
        result=backend.run(transpile(loaded,backend),shots=64,seed_simulator=19).result()
        self.assertTrue(result.success)
        counts=result.get_counts()
        self.assertEqual(sum(counts.values()),64)
        for bits in counts:
            packed=int(bits,2)
            self.assertEqual((packed>>9)&1,1)
            self.assertEqual((packed&7)*((packed>>3)&63),35)


if __name__=='__main__':
    unittest.main()

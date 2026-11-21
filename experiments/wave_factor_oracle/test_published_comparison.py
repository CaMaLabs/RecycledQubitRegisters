"""Published primitive transcription, coherent divider and Aer checks."""
import unittest
from comparison import benchmark
import qiskit_runner


class PublishedComparisonTests(unittest.TestCase):
    def test_primitive_matches_truth_table_and_paper_counts(self):
        self.assertEqual(benchmark.primitive_validation(),1360)

    def test_generic_divider_and_phase(self):
        self.assertEqual(benchmark.divider_validation(),992)

    def test_random_coherent_inputs(self):
        self.assertGreaterEqual(benchmark.coherent_validation(),120)

    def test_published_adapter_in_aer(self):
        result=qiskit_runner.run(323,5,2,128,19,architecture='published-cns')
        self.assertAlmostEqual(result['aer_success_probability'],0.908447265625,places=8)
        self.assertAlmostEqual(result['workspace_clean_mean_z'],1,places=8)
        self.assertEqual(result['logical_qubits'],38)
        self.assertTrue(set(result['measured_factor_pairs']).issubset({'17*19','19*17'}))

    def test_filter_only_probability_is_not_renormalized_to_one(self):
        result=qiskit_runner.run(323,5,0,128,19,architecture='published-cns')
        self.assertAlmostEqual(result['aer_success_probability'],0.0625,places=8)
        self.assertEqual(result['accepted_shots']+result['rejected_shots'],128)


if __name__=='__main__':
    unittest.main()

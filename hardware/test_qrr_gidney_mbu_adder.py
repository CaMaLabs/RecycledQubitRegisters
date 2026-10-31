"""Phase, reset, lowering, and branch-accounting contracts for the MBU adapter."""
import itertools
import math
import os
import random
import unittest

from qiskit import QuantumCircuit

import qrr_gidney_mbu_adder as adder
import qrr_gidney_mbu_audit as audit


@unittest.skipUnless(os.environ.get('QRR_GIDNEY_UPSTREAM'), 'pinned external checkout required')
class GidneyInstrumentContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        adder.load_upstream(os.environ['QRR_GIDNEY_UPSTREAM'])

    def test_affine_conjunction_elimination_including_shared_control(self):
        from constadd.circuit import Qubit, Bit, Parity
        qubits = Qubit('q').range(3)
        bits = Bit('b').range(2)
        rng = random.Random(20261031)
        for _ in range(100):
            rows = [Parity(frozenset(q for q in qubits if rng.randrange(2)),
                           frozenset(b for b in bits if rng.randrange(2)), bool(rng.randrange(2)))
                    for _ in range(3)]
            reduced = adder.canonical_controls(rows)
            for values in itertools.product((0,1),repeat=5):
                value = dict(zip(qubits+bits,values))
                def product(parities):
                    return all((sum(value[q] for q in p.qubits)+sum(value[b] for b in p.bits)+p.const)%2
                               for p in parities)
                self.assertEqual(product(rows), product(reduced))

    def test_complete_controlled_instrument_and_dirty_restoration(self):
        for variant in ('clean3','dirty2'):
            row = adder.exact_branch_proof(6,23,variant)
            self.assertTrue(row['branch_relative_phase_exact'])
            self.assertTrue(row['clean_restored'] and row['dirty_restored'])
            self.assertGreater(row['transcripts'],1)

    def test_missing_phase_correction_is_rejected(self):
        with self.assertRaises(AssertionError):
            adder.exact_branch_proof(6,23,omit_phase=True)

    def test_reset_cannot_erase_input_data(self):
        with self.assertRaisesRegex(AssertionError,'erase input-dependent'):
            adder.interpret_branch([('RZ',0,None,())],1,0)

    def test_actual_emitted_qiskit_preserves_coherent_input_in_every_branch(self):
        qc = QuantumCircuit(10)
        m = adder.append_adder(qc,list(range(6)),23,[6],list(range(7,10)))
        self.assertEqual(qc.count_ops()['reset'],m)
        initial = {x:1j**x.bit_count()/math.sqrt(128) for x in range(128)}
        expected = {(x & ~63) | (((x & 63)+23*(x >> 6 & 1))%64):a/math.sqrt(1<<m)
                    for x,a in initial.items()}
        for transcript in range(1<<m):
            actual,count = adder.sparse_qiskit_branch(qc,initial,transcript)
            self.assertEqual(count,m)
            self.assertEqual(actual.keys(),expected.keys())
            for x in expected:
                self.assertLess(abs(actual[x]-expected[x]),1e-12)

    def test_dynamic_native_metric_charges_conditional_cz(self):
        qc = QuantumCircuit(2,1)
        qc.measure(0,0)
        with qc.if_test((qc.clbits[0],1)):
            qc.cz(0,1)
            qc.cz(0,1)
        self.assertEqual(audit.recursive_counts(qc)['cz'],2)
        self.assertGreaterEqual(audit.structural_depth(qc),4)

    def test_patch_covers_both_cached_arithmetic_paths_and_restores(self):
        from types import SimpleNamespace
        before1, before2, replacement = object(), object(), object()
        src = SimpleNamespace(oldsel=SimpleNamespace(
            old=SimpleNamespace(one_bit_bypass_constant_add=before1),
            best=SimpleNamespace(constant_add_from_prefix_carry=before2)))
        with self.assertRaises(RuntimeError):
            with audit.patch_adders(src,replacement):
                self.assertIs(src.oldsel.old.one_bit_bypass_constant_add,replacement)
                self.assertIs(src.oldsel.best.constant_add_from_prefix_carry,replacement)
                raise RuntimeError('restore on failure')
        self.assertIs(src.oldsel.old.one_bit_bypass_constant_add,before1)
        self.assertIs(src.oldsel.best.constant_add_from_prefix_carry,before2)


if __name__ == '__main__':
    unittest.main()

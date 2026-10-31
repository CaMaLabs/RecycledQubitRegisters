"""Independent ideal-circuit and public-adapter contracts."""
import cmath
import math
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integrations.darkstar_hybrid import quaspy_public_postprocess as public
import qrr_indie_diamond_audit as audit


class SamplerContracts(unittest.TestCase):
    def test_distribution_matches_direct_shor_work_register_state(self):
        for n,a,r,bits in ((15,2,4,4),(21,2,6,4),(35,2,12,6)):
            Q=1<<bits
            mixture=[0.]*Q
            for z in range(r):
                for j,p in audit.head_bins(r,z,bits):
                    mixture[j]+=p/r
            self.assertAlmostEqual(sum(mixture),1.,places=12)
            for j in range(Q):
                amplitudes={}
                for x in range(Q):
                    w=pow(a,x,n)
                    amplitudes[w]=amplitudes.get(w,0)+cmath.exp(-2j*math.pi*x*j/Q)/Q
                exact=sum(abs(v)**2 for v in amplitudes.values())
                self.assertLess(abs(exact-mixture[j]),1e-12)

    def test_big_frequency_kernel_against_high_precision(self):
        import mpmath as mp
        mp.mp.dps=100
        r,z,bits=123456789012345678901,123456789001,160
        Q=1<<bits
        for j,p in audit.head_bins(r,z,bits):
            v=(j*r-z*Q)%(Q*r)
            if 2*v>Q*r:v-=Q*r
            x=mp.mpf(v)/r
            expected=(mp.sin(mp.pi*x)/(Q*mp.sin(mp.pi*x/Q)))**2 if v else 1
            self.assertLess(abs(float(expected)-p),1e-12)

    def test_tail_is_censored_without_renormalizing(self):
        r,z,bits=37,11,24
        mass=sum(p for _,p in audit.head_bins(r,z,bits))
        self.assertLess(mass,1.)
        j,reported=audit.draw_head(r,z,bits,(mass+1)/2)
        self.assertIsNone(j)
        self.assertAlmostEqual(reported,mass)

    def test_public_replay_rejects_oracle_fields(self):
        with self.assertRaises(ValueError):
            public.replay(dict(N=35,base=2,phase_bits=8,frequency=42,r=12))


@unittest.skipUnless(os.environ.get('QRR_QUASPY_UPSTREAM'),'pinned external checkout required')
class AdapterContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        public.load_upstream(os.environ['QRR_QUASPY_UPSTREAM'])

    def test_signed_group_powers_and_identity(self):
        from gmpy2 import mpz
        ledger=public.Ledger()
        g=public.group_element(2,35,ledger)
        self.assertTrue(g**12==1)
        self.assertTrue(g**12==mpz(1))
        self.assertTrue((g**-1)*g==1)
        self.assertEqual(ledger.inverse_calls,1)

    def test_strict_factor_verification_and_work_cap(self):
        answer=public.recover(35,2,8,42)
        self.assertEqual(answer['factors'],[5,7])
        limited=public.recover(35,2,8,42,budget=0)
        self.assertEqual(limited['status'],'WORK_LIMIT')
        self.assertIsNone(limited['factors'])

    def test_small_smooth_order_can_succeed_without_measurement(self):
        # This is precisely why the primary audit also includes null controls.
        answer=public.recover(35,2,8,0)
        self.assertEqual(answer['factors'],[5,7])
        baseline=public.recover(35,2,8,0,'cf')
        self.assertIsNone(baseline['factors'])


if __name__=='__main__':
    unittest.main()

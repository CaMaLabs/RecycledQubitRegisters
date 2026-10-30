"""Independent numerical contracts for the refinement audit adapter."""
import os
import math
import unittest
import numpy as np
import qrr_bayesian_refinement_audit as audit


class CassiniContract(unittest.TestCase):
    def test_exact_adversarial_alias(self):
        result=audit.cassini_obstruction()
        self.assertEqual(result['status'],'EXACT_ALGEBRA_PASS')
        self.assertLess(result['rows'][-1]['independent_probe_transcript_TV_upper_bound_48_probes'],1e-38)

    def test_actual_accumulator_probe_conjugation(self):
        fib=[0,1]
        for _ in range(10):fib.append(fib[-1]+fib[-2])
        cases=0
        for modulus in (15,21,35):
            units=[x for x in range(modulus) if math.gcd(x,modulus)==1]
            for t in range(1,8):
                for x in units:
                    for y in units:
                        for register in (0,1):
                            u,v=x,y
                            for _ in range(t):u,v=v*pow(u,-1,modulus)%modulus,u
                            if register==0:u=u*2%modulus
                            else:v=v*2%modulus
                            for _ in range(t):u,v=v,u*v%modulus
                            a,b=(fib[t-1],fib[t]) if register==0 else (fib[t],fib[t+1])
                            self.assertEqual((u,v),(x*pow(2,a,modulus)%modulus,y*pow(2,b,modulus)%modulus))
                            cases+=1
        self.assertEqual(cases,10976)


@unittest.skipUnless(os.environ.get('QRR_UPSTREAM_SIMULATOR'),'external simulator path required')
class RefinementContract(unittest.TestCase):
    def setUp(self):
        self.u=audit.load_upstream(os.environ['QRR_UPSTREAM_SIMULATOR'])
        self.Q=1<<32

    def test_uniform_prior_conserves_geometric_cell_mass(self):
        p=audit.global_class(self.u)(self.Q)
        for i in (0,1,0,2,31):p.split(i,[])
        np.testing.assert_allclose(p.masses(),p.widths(),atol=1e-13,rtol=0)
        self.assertAlmostEqual(p.masses().sum(),1.)

    def test_split_weights_match_independent_full_likelihood(self):
        p=audit.global_class(self.u)(self.Q)
        history=[self.u.Observation(1,0,0),self.u.Observation(1,self.Q//4,1)]
        for observation in history:p.update(*observation)
        for i in (0,1,0):p.split(i,history)
        np.testing.assert_allclose(p.masses(),audit.full_weights(self.u,p,history),atol=1e-13,rtol=0)


if __name__=='__main__':unittest.main()

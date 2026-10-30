"""Certificate and budget guards for the public-input RSA attack runner."""
import math
import unittest
import rsa_zero_cost_attack as attack


class AttackContract(unittest.TestCase):
    def test_divisor_must_be_proper_and_exact(self):
        for bad in (0,1,6,35,70):
            self.assertIsNone(attack.factors_from_divisor(35,bad))
        self.assertEqual(attack.factors_from_divisor(35,5),[5,7])

    def test_public_recovered_key_roundtrips(self):
        result=attack.validate_recovery(61*53,17,[53,61])
        self.assertTrue(result['rsa_private_exponent_available'])
        self.assertEqual(result['public_roundtrip_checks'],7)

    def test_wrong_factor_certificate_is_rejected(self):
        with self.assertRaises(AssertionError):
            attack.validate_recovery(35,5,[5,11])

    def test_small_d_recovery_uses_only_public_key(self):
        n=1009*1013;phi=1008*1012;d=5
        self.assertEqual(math.gcd(d,phi),1)
        factors,details=attack.wiener(n,pow(d,-1,phi))
        self.assertEqual(factors,[1009,1013])

    def test_timeout_is_censored(self):
        result=attack.run_arm(attack.RSA2048,65537,'ecm',.0001)
        self.assertEqual(result['status'],'TIMEOUT_CENSORED')


if __name__=='__main__':unittest.main()

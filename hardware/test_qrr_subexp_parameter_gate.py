import unittest
import qrr_subexp_parameter_gate as gate


class FiniteParameterContracts(unittest.TestCase):
    def test_rsa2048_has_zero_speedup_levels_and_prohibitive_literal_loops(self):
        p = gate.parameters(2048)
        self.assertEqual(p['recursive_levels'],0)
        self.assertEqual(p['s'],3)
        self.assertEqual(p['top_width'],90192960553530)
        self.assertEqual(p['top_table_power_of_two_exponent'],4329262106569440)
        self.assertEqual(p['bottom_enumeration_iterations_log2'],207804581115333120)

    def test_exact_level_transition(self):
        threshold = (9*48**16)**40
        self.assertEqual(gate.parameters(threshold-1)['recursive_levels'],0)
        self.assertEqual(gate.parameters(threshold)['recursive_levels'],1)
        self.assertEqual(len(str(threshold)),1115)

    def test_accelerated_level_search_matches_literal_iteration(self):
        for n in (0,1,2,16,128,2048):
            ell = 0
            for _ in range(n):
                group = 48
                for _ in range(ell+1):
                    group = 9*group**16
                if group**40 <= n:
                    ell += 1
            self.assertEqual(gate.parameters(n)['recursive_levels'],ell)


if __name__ == '__main__':
    unittest.main()

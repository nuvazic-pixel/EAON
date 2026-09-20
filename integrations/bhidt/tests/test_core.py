import unittest
from physics.schwarzschild import schwarzschild_radius,hawking_temperature,bekenstein_hawking_entropy
from physics.evaporation import evaporation_time,mass_at_tau
from information.entropy import find_page_time,entropy_state
class TestCore(unittest.TestCase):
    def test_scalings(self):
        m=1e20
        self.assertAlmostEqual(schwarzschild_radius(2*m)/schwarzschild_radius(m),2)
        self.assertAlmostEqual(hawking_temperature(2*m)/hawking_temperature(m),0.5)
        self.assertAlmostEqual(bekenstein_hawking_entropy(2*m)/bekenstein_hawking_entropy(m),4)
        self.assertAlmostEqual(evaporation_time(2*m)/evaporation_time(m),8)
    def test_mass_decreases(self):
        vals=[mass_at_tau(1e12,x) for x in [0,.2,.5,.8,.99]]
        self.assertTrue(all(a>b for a,b in zip(vals,vals[1:])))
    def test_page_transition(self):
        pt=find_page_time()
        self.assertTrue(0<pt<1)
        self.assertEqual(entropy_state(pt-.1)["dominant_saddle"],"NO_ISLAND")
        self.assertEqual(entropy_state(pt+.1)["dominant_saddle"],"ISLAND")
    def test_final_entropy(self):
        self.assertLess(entropy_state(.999999)["radiation_entropy"],.02)
if __name__=="__main__": unittest.main()

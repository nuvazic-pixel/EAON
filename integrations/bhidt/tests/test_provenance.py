import unittest
from engine.simulation import BlackHoleSimulation
from engine.explain import explain_field, explain_transition

class TestProvenance(unittest.TestCase):
    def setUp(self):
        self.sim = BlackHoleSimulation(1e12)

    def test_temperature_has_equation_and_source(self):
        s = self.sim.snapshot(0.2)
        e = explain_field(s, "hawking_temperature_K")
        self.assertEqual(e["equation_id"], "HAWK-T")
        self.assertTrue(e["sources"])
        self.assertIn("semiclassical", e["model_scope"])

    def test_page_time_marked_non_universal(self):
        s = self.sim.snapshot(0.2)
        e = explain_field(s, "page_time")
        self.assertEqual(e["model_scope"], "model_derived_not_universal")

    def test_transition_explanation(self):
        pt = self.sim.page_time
        before = self.sim.snapshot(pt - 0.01)
        after = self.sim.snapshot(pt + 0.01)
        e = explain_transition(before, after)
        self.assertTrue(e["transition_detected"])
        self.assertEqual(e["from"], "NO_ISLAND")
        self.assertEqual(e["to"], "ISLAND")
        self.assertIsNotNone(e["reason"])

if __name__ == "__main__": unittest.main()

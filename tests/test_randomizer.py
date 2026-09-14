"""Tests for the seeded hierarchical RNG (seedian pattern, #163)."""

import unittest

from btools.utils.randomizer import BToolsRandom


class TestBToolsRandom(unittest.TestCase):
    def test_reproducible(self):
        a = BToolsRandom("seed-1")
        b = BToolsRandom("seed-1")
        for _ in range(10):
            self.assertEqual(
                a.rng("facade", "window", 3).random(),
                b.rng("facade", "window", 3).random(),
            )

    def test_branch_independence(self):
        # -- draws from one path are unaffected by other paths being drawn
        solo = BToolsRandom("s")
        mixed = BToolsRandom("s")
        _ = mixed.rng("roof").random()
        _ = mixed.choice(("x",), ("a", "b"))
        _ = mixed.chance(("balcony", 2), 0.5)
        self.assertEqual(solo.rng("facade").random(), mixed.rng("facade").random())

    def test_seed_sensitivity(self):
        self.assertNotEqual(
            BToolsRandom("s1").rng("x").random(), BToolsRandom("s2").rng("x").random()
        )

    def test_root_stream_forbidden(self):
        with self.assertRaises(ValueError):
            BToolsRandom("s").rng()

    def test_decision_log(self):
        r = BToolsRandom("s")
        r.choice(("p",), ("BAR", "PANELS"))
        r.chance(("p", "q"), 0.5)
        self.assertEqual(len(r.decisions), 2)
        path, decision, value = r.decisions[0]
        self.assertEqual(path, "p")
        self.assertEqual(decision, "choice")
        self.assertIn(value, ("BAR", "PANELS"))

    def test_helpers(self):
        r = BToolsRandom("s")
        self.assertTrue(0.9 <= r.jitter(("j",), 1.0, 0.1) <= 1.1)
        self.assertIn(r.weighted_choice(("w",), "AB", [1, 0]), ("A", "B"))
        # -- zero weight: the other option can never be picked
        self.assertEqual(r.weighted_choice(("w2",), "AB", [1, 0]), "A")


if __name__ == "__main__":
    unittest.main()

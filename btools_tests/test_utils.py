import btools
import unittest


class TestUtilsCommon(unittest.TestCase):

    def test_equal(self):
        self.assertTrue(btools.utils.equal(0.005, 0.006))

    def test_clamp(self):
        self.assertEqual(btools.utils.clamp(2, 0.2, 1), 1)
        self.assertEqual(btools.utils.clamp(0.1, 0.2, 1), 0.2)

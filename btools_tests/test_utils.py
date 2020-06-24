import bmesh
import btools
import unittest


class TestUtilsCommon(unittest.TestCase):

    def test_equal(self):
        # -- default eps(0.001)
        self.assertTrue(btools.utils.equal(0.005, 0.006))
        self.assertFalse(btools.utils.equal(0.005, 0.0061))

        # -- higher eps(0.0001)
        self.assertFalse(btools.utils.equal(0.005, 0.006, 0.0001))

    def test_clamp(self):
        self.assertEqual(btools.utils.clamp(2, 0.2, 1), 1)
        self.assertEqual(btools.utils.clamp(0.1, 0.2, 1), 0.2)

    def test_restricted_sizeoffset(self):
        # XXX OFFSET
        # -- restrict sane
        self.assertEqual(
            btools.utils.restricted_offset([1, 1], [0.5, 0.5], [0, 0]), (0, 0))

        # -- restrict min
        self.assertEqual(
            btools.utils.restricted_offset([1, 1], [0.5, 0.5], [-1, -1]), (-0.25, -0.25))

        # -- restrict max
        self.assertEqual(
            btools.utils.restricted_offset([1, 1], [0.5, 0.5], [1, 1]), (0.25, 0.25))

        # XXX SIZE
        # -- restrict sane
        self.assertEqual(
            btools.utils.restricted_size([1, 1], [0, 0], [0, 0], [0.5, 0.5]), (0.5, 0.5))

        # -- restrict min
        self.assertEqual(
            btools.utils.restricted_size([1, 1], [0, 0], [1, 1], [0.5, 0.5]), (1, 1))

        # -- restrict with offset
        self.assertEqual(
            btools.utils.restricted_size([1, 1], [0.5, 0.5], [0.5, 0.5], [0.75, 0.75]), (0.5, 0.5))

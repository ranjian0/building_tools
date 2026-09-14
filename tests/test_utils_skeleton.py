import unittest

from mathutils import Vector

import btools


def _snap(arcs):
    """Normalize skeleton output for structural comparison."""
    return sorted(
        (
            tuple(round(c, 6) for c in arc.source),
            round(arc.height, 6),
            frozenset(tuple(round(c, 6) for c in sink) for sink in arc.sinks),
        )
        for arc in arcs
    )


class TestSkeletonize(unittest.TestCase):
    def test_square(self):
        # clockwise winding (the winding the roof code feeds via link_loop_prev)
        square = [(0, 0), (0, 10), (10, 10), (10, 0)]
        arcs = btools.utils.skeletonize(square, [])
        self.assertEqual(len(arcs), 2)
        for arc in arcs:
            self.assertEqual(arc.source.to_tuple(), (5.0, 5.0))
            self.assertAlmostEqual(arc.height, 5.0, places=6)

    def test_rectangle_gable(self):
        rect = [(0, 0), (0, 10), (20, 10), (20, 0)]
        arcs = btools.utils.skeletonize(rect, [], zero_gradient=True)
        self.assertEqual(len(arcs), 2)
        sources = sorted(arc.source.to_tuple() for arc in arcs)
        self.assertEqual(sources, [(0.0, 5.0), (20.0, 5.0)])
        for arc in arcs:
            self.assertAlmostEqual(arc.height, 5.0, places=6)

    def test_l_shape(self):
        l_shape = [(0, 0), (0, 10), (10, 10), (10, 20), (20, 20), (20, 0)]
        arcs = btools.utils.skeletonize(l_shape, [])
        self.assertEqual(len(arcs), 4)
        heights = {round(arc.height, 6) for arc in arcs}
        self.assertEqual(heights, {5.0})

    def test_hole(self):
        outer = [(0, 0), (0, 20), (20, 20), (20, 0)]
        hole = [(5, 5), (15, 5), (15, 15), (5, 15)]
        arcs = btools.utils.skeletonize(outer, [hole])
        self.assertEqual(len(arcs), 2)

    def test_deterministic(self):
        square = [(0, 0), (0, 10), (10, 10), (10, 0)]
        first = _snap(btools.utils.skeletonize(square, []))
        second = _snap(btools.utils.skeletonize(square, []))
        self.assertEqual(first, second)

    def test_result_types(self):
        square = [(0, 0), (0, 10), (10, 10), (10, 0)]
        for arc in btools.utils.skeletonize(square, []):
            self.assertIsInstance(arc.source, Vector)
            self.assertGreater(arc.height, 0.0)
            for sink in arc.sinks:
                self.assertIsInstance(sink, Vector)


if __name__ == "__main__":
    unittest.main()

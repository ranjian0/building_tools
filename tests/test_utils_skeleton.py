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

    def test_arc_faces_square(self):
        # -- every arc is flanked by its sink vertex's two edge faces; on a
        #    square those are corner-adjacent pairs plus possibly one
        #    merged-vertex pair (e.g. (3, 1) once an edge has collapsed)
        square = [(0, 0), (0, 10), (10, 10), (10, 0)]
        arcs = btools.utils.skeletonize(square, [])
        seen = set()
        for arc in arcs:
            self.assertEqual(len(arc.faces), len(arc.sinks))
            for f0, f1 in arc.faces:
                self.assertIn(f0, range(4))
                self.assertIn(f1, range(4))
                self.assertNotEqual(f0, f1)
                seen.add((f0, f1))
        self.assertGreaterEqual(len(seen), 4)

    def test_arc_faces_merged_vertices(self):
        # -- L-shape: merged/split vertices carry non-adjacent edge pairs
        l_shape = [(0, 0), (0, 10), (10, 10), (10, 20), (20, 20), (20, 0)]
        arcs = btools.utils.skeletonize(l_shape, [])
        adjacent = {(i, (i + 1) % 6) for i in range(6)}
        merged = set()
        for arc in arcs:
            for f in arc.faces:
                self.assertTrue(all(0 <= e < 6 for e in f), f)
                if f not in adjacent:
                    merged.add(f)
        self.assertTrue(merged, "expected at least one merged-vertex arc")

    def test_hole_edge_ids_continue(self):
        # -- hole contour edges continue the numbering after the outline
        outer = [(0, 0), (0, 20), (20, 20), (20, 0)]
        hole = [(5, 5), (15, 5), (15, 15), (5, 15)]
        arcs = btools.utils.skeletonize(outer, [hole])
        pairs = [f for arc in arcs for f in arc.faces]
        self.assertTrue(pairs)
        for f in pairs:
            self.assertTrue(all(0 <= e < 8 for e in f), f)


if __name__ == "__main__":
    unittest.main()

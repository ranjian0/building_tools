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
        # -- symmetric ring: the exact-tie degeneracy engages the jitter
        #    retry, producing a structurally complete skeleton (every hole
        #    and outline edge covered by some arc's faces, no ghost arcs
        #    above the channel half-width)
        outer = [(0, 0), (0, 20), (20, 20), (20, 0)]
        hole = [(5, 5), (15, 5), (15, 15), (5, 15)]
        arcs = btools.utils.skeletonize(outer, [hole])
        self.assertGreaterEqual(len(arcs), 2)
        covered = {e for arc in arcs for f in arc.faces for e in f}
        self.assertEqual(covered, set(range(8)))
        for arc in arcs:
            self.assertLessEqual(arc.height, 2.5 + 1e-3, arc.height)

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

    def test_weighted_unit_weights_match_unweighted(self):
        # -- weights of 1.0 must reproduce the classic path exactly
        square = [(0, 0), (0, 10), (10, 10), (10, 0)]
        plain = _snap(btools.utils.skeletonize(square, []))
        weighted = _snap(btools.utils.skeletonize(square, [], weights=[1.0] * 4))
        self.assertEqual(plain, weighted)

    def test_weighted_rectangle_ridge(self):
        # -- rect [(0,0),(0,10),(20,10),(20,0)]: edges 0/2 long, 1/3 short.
        #    ridge z = w_long * W/2; ridge length = L - w_long*W/w_short
        rect = [(0, 0), (0, 10), (20, 10), (20, 0)]

        # -- longs 45deg (w=1), shorts 63.43deg (w=2): ridge 15 long at z 5
        arcs = btools.utils.skeletonize(rect, [], weights=[1.0, 2.0, 1.0, 2.0])
        peaks = sorted((round(a.source.x, 3), round(a.height, 3)) for a in arcs)
        self.assertEqual(peaks, [(2.5, 5.0), (17.5, 5.0)])

        # -- longs steep (w=2), shorts shallow (w=1): the ridge collapses
        #    to zero length -- a single pyramid peak at z 10 (possibly
        #    reported as two coincident subtrees)
        arcs = btools.utils.skeletonize(rect, [], weights=[2.0, 1.0, 2.0, 1.0])
        peaks = sorted(
            (round(a.source.x, 3), round(a.source.y, 3), round(a.height, 3))
            for a in arcs
        )
        self.assertLessEqual(len(peaks), 2)
        for x, y, h in peaks:
            self.assertAlmostEqual(x, 10.0, places=3)
            self.assertAlmostEqual(y, 5.0, places=3)
            self.assertAlmostEqual(h, 10.0, places=3)


if __name__ == "__main__":
    unittest.main()

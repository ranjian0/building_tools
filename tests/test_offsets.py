"""Tests for skeleton-derived mitered offsets (util_offsets)."""

import unittest

import btools


def bbox(ring):
    xs = [p.x for p in ring]
    ys = [p.y for p in ring]
    return (min(xs), min(ys), max(xs), max(ys))


def signed_area(ring):
    total = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i].x, ring[i].y
        x1, y1 = ring[(i + 1) % n].x, ring[(i + 1) % n].y
        total += x0 * y1 - x1 * y0
    return total / 2.0


class TestOffsetPolygons(unittest.TestCase):
    SQUARE = [(0, 0), (0, 10), (10, 10), (10, 0)]
    RECT = [(0, 0), (0, 10), (20, 10), (20, 0)]
    L_SHAPE = [(0, 0), (0, 10), (10, 10), (10, 20), (20, 20), (20, 0)]

    def test_square(self):
        sk = btools.utils.skeletonize(self.SQUARE, [])
        rings = btools.utils.offset_polygons(sk, self.SQUARE, 2.0)
        self.assertEqual(len(rings), 1)
        ring = rings[0]
        self.assertEqual(len(ring), 4)
        for v in (2.0, 8.0):
            self.assertIn(round(v, 4), [round(p.x, 4) for p in ring])
            self.assertIn(round(v, 4), [round(p.y, 4) for p in ring])
        self.assertLess(signed_area(ring), 0.0)  # clockwise like the input

    def test_rectangle(self):
        sk = btools.utils.skeletonize(self.RECT, [])
        rings = btools.utils.offset_polygons(sk, self.RECT, 2.0)
        self.assertEqual(len(rings), 1)
        b = bbox(rings[0])
        for got, want in zip(b, (2.0, 2.0, 18.0, 8.0)):
            self.assertAlmostEqual(got, want, places=4)

    def test_beyond_max_height_empty(self):
        for pts, d in ((self.SQUARE, 5.5), (self.RECT, 5.5), (self.L_SHAPE, 5.5)):
            sk = btools.utils.skeletonize(pts, [])
            self.assertEqual(btools.utils.offset_polygons(sk, pts, d), [])

    def test_l_shape_single_ring(self):
        # -- the eroded L stays one connected ring until the arms vanish
        sk = btools.utils.skeletonize(self.L_SHAPE, [])
        for d in (2.0, 4.5):
            rings = btools.utils.offset_polygons(sk, self.L_SHAPE, d)
            self.assertEqual(len(rings), 1, d)
            b = bbox(rings[0])
            for got, want in zip(b, (d, d, 20 - d, 20 - d)):
                self.assertAlmostEqual(got, want, places=4)

    def test_invalid_distance(self):
        sk = btools.utils.skeletonize(self.SQUARE, [])
        with self.assertRaises(ValueError):
            btools.utils.offset_polygons(sk, self.SQUARE, 0.0)

    def test_star_offsets(self):
        # -- tie-degenerate tangential star: the correct skeleton is the
        #    center fan; offsets at any depth must give one closed ring
        import math

        pts = []
        for i in range(16):
            r = 6.0 if i % 2 == 0 else 2.5
            a = 2 * math.pi * i / 16
            pts.append((r * math.cos(a), r * math.sin(a)))
        area = (
            sum(
                pts[i][0] * pts[(i + 1) % 16][1] - pts[(i + 1) % 16][0] * pts[i][1]
                for i in range(16)
            )
            / 2
        )
        if area > 0:
            pts = pts[::-1]

        sk = btools.utils.skeletonize(pts, [])
        max_h = max(a.height for a in sk)
        for frac in (0.15, 0.5, 0.9):
            rings = btools.utils.offset_polygons(sk, pts, max_h * frac)
            self.assertEqual(len(rings), 1, frac)
            self.assertGreaterEqual(len(rings[0]), 8, frac)
            self.assertLess(signed_area(rings[0]), 0.0, frac)  # clockwise

    def test_apse_offsets(self):
        # -- semicircular protrusion (multi-edge-collapse class): the
        #    terminal drain closes it; the offset ring must follow the bump
        import math

        segs, r, w, h = 16, 2.0, 10.0, 8.0
        pts = [(-w / 2, -h / 2), (-w / 2, h / 2)]
        for i in range(segs + 1):
            a = math.pi / 2 - math.pi * i / segs
            pts.append((w / 2 + r * math.cos(a), r * math.sin(a)))
        pts.append((w / 2, -h / 2))
        area = (
            sum(
                pts[i][0] * pts[(i + 1) % len(pts)][1]
                - pts[(i + 1) % len(pts)][0] * pts[i][1]
                for i in range(len(pts))
            )
            / 2
        )
        if area > 0:
            pts = pts[::-1]

        sk = btools.utils.skeletonize(pts, [])
        covered = {e for arc in sk for f in arc.faces for e in f}
        self.assertEqual(covered, set(range(len(pts))))
        rings = btools.utils.offset_polygons(sk, pts, 0.5)
        self.assertEqual(len(rings), 1)
        xs = [p.x for p in rings[0]]
        # -- the bump apex offsets inward by ~0.5 (within the 16-segment
        #    discretization slack of the arc)
        self.assertAlmostEqual(max(xs), (w / 2 + r) - 0.5, delta=0.03)


if __name__ == "__main__":
    unittest.main()

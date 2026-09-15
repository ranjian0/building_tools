"""Tests for interior partitions (roadmap item 7, phases 2-3)."""

import unittest

import btools
from btools.utils import Rect, adjacency_segments, spanning_doors, squarify


class TestSquarify(unittest.TestCase):
    def test_exact_area_and_coverage(self):
        for areas in ([2, 1, 1], [1] * 4, [3, 2, 2, 1, 1, 1], [5]):
            rects = squarify(Rect(0, 0, 10, 8), areas)
            self.assertEqual(len(rects), len(areas))
            self.assertAlmostEqual(sum(r.w * r.h for r in rects), 80.0, places=6)
            for r in rects:
                self.assertGreater(r.w, 0)
                self.assertGreater(r.h, 0)

    def test_reasonable_aspects(self):
        rects = squarify(Rect(0, 0, 10, 8), [2, 1, 1])
        worst = max(max(r.w / r.h, r.h / r.w) for r in rects)
        self.assertLess(worst, 2.0)

    def test_degenerate(self):
        self.assertEqual(squarify(Rect(0, 0, 10, 8), []), [])
        self.assertEqual(squarify(Rect(0, 0, 0, 8), [1, 1]), [])


class TestAdjacency(unittest.TestCase):
    def test_two_rooms_share_border(self):
        rects = [Rect(0, 0, 5, 8), Rect(5, 0, 5, 8)]
        segs = adjacency_segments(rects)
        self.assertEqual(len(segs), 1)
        (i, j), ((x0, y0), (x1, y1)) = segs[0]
        self.assertEqual((i, j), (0, 1))
        self.assertAlmostEqual(x0, 5.0)
        self.assertAlmostEqual(y0, 0.0)
        self.assertAlmostEqual(y1, 8.0)

    def test_spanning_doors_count(self):
        rects = squarify(Rect(0, 0, 10, 8), [1] * 6)
        doors = spanning_doors(adjacency_segments(rects), 0.9)
        self.assertEqual(len(doors), 5)  # n-1 doors keep 6 rooms connected

    def test_spanning_doors_jitter_reproducible(self):
        import random

        rects = squarify(Rect(0, 0, 10, 8), [1] * 4)
        segs = adjacency_segments(rects)
        d1 = spanning_doors(segs, 0.9, random.Random(7))
        d2 = spanning_doors(segs, 0.9, random.Random(7))
        self.assertEqual(d1, d2)


class TestPartitions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_api_options

        test_api_options.register_all()

    def setUp(self):
        import bpy

        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)

    @staticmethod
    def _build(interior_kwargs, floor_kwargs=None, width=10.0, length=8.0):
        import bpy

        from btools.api import FaceTarget, apply_feature
        from btools.api.core import options_from_dict
        from btools.api.options import FloorOptions, FloorplanOptions, InteriorOptions

        floor_kwargs = floor_kwargs or {
            "floor_count": 1,
            "floor_height": 3.0,
            "wall_thickness": 0.2,
        }
        res = apply_feature(
            "floorplan",
            options_from_dict(FloorplanOptions, {"width": width, "length": length}),
        )
        obj = bpy.data.objects[res.created_object]
        apply_feature(
            "floor", options_from_dict(FloorOptions, floor_kwargs), FaceTarget(obj)
        )
        # ground interior/full floor face
        me = obj.data
        names = [mt.name for mt in getattr(obj, "bt_materials", [])]
        attr = me.attributes.get(".bt_material_group_index")
        vals = [0] * len(me.polygons)
        attr.data.foreach_get("value", vals)
        z_floor = 0.2 if floor_kwargs.get("wall_thickness") else 0.0
        idx = None
        for i, (p, t) in enumerate(zip(me.polygons, vals)):
            if (
                names[t] in ("slabs", "roof")
                and p.normal.z > 0.9
                and abs(p.center.z - z_floor) < 0.05
                and p.area > 70
            ):
                idx = i
                break
        if idx is None:
            raise AssertionError("no floor face found at z~%.2f" % z_floor)
        res = apply_feature(
            "interior",
            options_from_dict(InteriorOptions, interior_kwargs),
            FaceTarget(obj, [idx]),
        )
        return obj, res

    @staticmethod
    def _partition_faces(obj):
        me = obj.data
        names = [mt.name for mt in getattr(obj, "bt_materials", [])]
        attr = me.attributes.get(".bt_material_group_index")
        vals = [0] * len(me.polygons)
        attr.data.foreach_get("value", vals)
        return [
            p
            for p, t in zip(me.polygons, vals)
            if names[t] == "walls" and 0.1 < p.center.z < 2.9
        ]

    def test_treemap_partitions_and_doors(self):
        obj, res = self._build(
            {
                "partition_mode": "TREEMAP",
                "room_count": 4,
                "inset": 0.2,
                "partition_height": 2.5,
                "door_width": 0.9,
                "door_height": 2.1,
            },
            floor_kwargs={
                "floor_count": 1,
                "floor_height": 3.0,
                "wall_thickness": 0.2,
            },
        )
        self.assertTrue(res.ok, res.errors)
        parts = self._partition_faces(obj)
        self.assertGreaterEqual(len(parts), 20)  # wall boxes + headers
        # door headers exist above door height
        headers = [p for p in parts if p.center.z > 2.0]
        self.assertEqual(len(headers) >= 3, True)  # >= rooms - 1 doors

        from btools.api.validate import validate_object

        report = validate_object(obj, include_geometry=False)
        self.assertTrue(report["ok"], report["problems"])

    def test_skeleton_core_ring(self):
        obj, res = self._build(
            {
                "partition_mode": "SKELETON",
                "min_corridor": 3.0,
                "partition_height": 2.5,
                "door_width": 0.9,
                "door_height": 2.1,
            },
        )
        self.assertTrue(res.ok, res.errors)
        parts = self._partition_faces(obj)
        self.assertGreaterEqual(len(parts), 10)
        # core ring for a 10x8 at depth 3: walls at |x|=2, |y|=1
        xs = {round(p.center.x, 1) for p in parts}
        ys = {round(p.center.y, 1) for p in parts}
        self.assertTrue(any(abs(abs(x) - 2.0) < 0.15 for x in xs), xs)
        self.assertTrue(any(abs(abs(y) - 1.0) < 0.15 for y in ys), ys)

    def test_room_count_drives_partitions(self):
        obj4, _ = self._build({"partition_mode": "TREEMAP", "room_count": 4})
        obj7, _ = self._build({"partition_mode": "TREEMAP", "room_count": 7})
        self.assertGreater(
            len(self._partition_faces(obj7)), len(self._partition_faces(obj4))
        )

    def test_default_mode_is_treemap(self):
        from btools.api.options import InteriorOptions

        self.assertEqual(InteriorOptions().partition_mode.value, "TREEMAP")


if __name__ == "__main__":
    unittest.main()

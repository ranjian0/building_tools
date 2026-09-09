"""Headless smoke tests for the scriptable api (btools.api).

Covers the deterministic control surface: explicit targets, structured
OpResults, and validation-driven assertions.
"""

import unittest

import bpy

import btools
from btools.api import (
    DoorOptions,
    FaceTarget,
    FloorOptions,
    FloorplanOptions,
    RoofOptions,
    apply_feature,
)
from btools.api.validate import validate_object


def clean_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)


def top_face(obj):
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()  # fresh bmeshes have unset (0) indices
    top_z = max(f.calc_center_median().z for f in bm.faces)
    cands = [f for f in bm.faces if abs(f.calc_center_median().z - top_z) < 1e-4]
    idx = max(cands, key=lambda f: f.calc_area()).index
    bm.free()
    return idx


def ground_wall_face(obj):
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    picked = [
        f.index
        for f in bm.faces
        if abs(f.normal.z) < 0.001
        and f.calc_center_median().z < 3.0
        and f.calc_area() > 1.0
    ]
    bm.free()
    return picked[0]


class TestApiSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # -- ensure all property groups (and their pointer targets) exist:
        #    the options tests unregister their copies on teardown
        import test_api_options

        test_api_options.register_all()

    def setUp(self):
        clean_scene()

    def test_floorplan_result(self):
        res = apply_feature("floorplan", FloorplanOptions(width=6, length=5))
        self.assertTrue(res.ok)
        self.assertIn(res.created_object, bpy.data.objects)
        obj = bpy.data.objects[res.created_object]
        self.assertEqual(len(obj.data.polygons), 1)

        # -- fresh floorplan has no matgroup layer: validation must pass
        report = validate_object(obj)
        self.assertTrue(report["ok"], report["problems"])

    def test_full_building(self):
        res = apply_feature("floorplan", FloorplanOptions(width=8, length=6))
        self.assertTrue(res.ok)
        obj = bpy.data.objects[res.created_object]

        res = apply_feature("floor", FloorOptions(floor_count=2, floor_height=3.0), FaceTarget(obj))
        self.assertTrue(res.ok, res.errors)
        for group in ("walls", "roof", "slabs"):
            self.assertGreater(res.matgroup_counts.get(group, 0), 0, group)

        res = apply_feature("roof", RoofOptions(type="HIP", height=1.0), FaceTarget(obj, [top_face(obj)]))
        self.assertTrue(res.ok, res.errors)
        self.assertGreater(res.matgroup_counts.get("roof_hangs", 0), 0)

        res = apply_feature("door", DoorOptions(), FaceTarget(obj, [ground_wall_face(obj)]))
        self.assertTrue(res.ok, res.errors)
        for group in ("door", "frame"):
            self.assertGreater(res.matgroup_counts.get(group, 0), 0, group)

        report = validate_object(
            obj,
            expect={"groups": ["walls", "roof", "slabs", "door", "frame"]},
            include_geometry=False,
        )
        self.assertTrue(report["ok"], report["problems"])

    def test_invalid_target_reports_cancelled(self):
        res = apply_feature("floorplan", FloorplanOptions(width=4, length=4))
        obj = bpy.data.objects[res.created_object]
        apply_feature("floor", FloorOptions(floor_count=2), FaceTarget(obj))
        # -- top face (z~6) + ground wall face (z~1.5): not coplanar -> cancelled
        res = apply_feature(
            "floor", FloorOptions(), FaceTarget(obj, [top_face(obj), ground_wall_face(obj)])
        )
        self.assertEqual(res.status, "cancelled")
        self.assertTrue(res.errors)

    def test_unknown_feature_raises(self):
        with self.assertRaises(ValueError):
            apply_feature("nonsense", None)


if __name__ == "__main__":
    unittest.main()

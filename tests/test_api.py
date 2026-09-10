"""Headless smoke tests for the scriptable api (btools.api).

Covers the deterministic control surface: explicit targets, structured
OpResults, and validation-driven assertions.
"""

import unittest

import bpy

from btools.api import (
    BalconyOptions,
    DoorOptions,
    FaceTarget,
    FloorOptions,
    FloorplanOptions,
    RoofOptions,
    SizeOffsetOptions,
    WindowOptions,
    apply_feature,
)
from btools.api.validate import validate_object


def make_wall():
    """6 x 0.4 x 3 wall box; front face (-Y) is the canonical element target."""
    import bmesh

    me = bpy.data.meshes.new("wall_mesh")
    obj = bpy.data.objects.new("wall", me)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = (v.co.x * 6.0, v.co.y * 0.4, (v.co.z + 0.5) * 3.0)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    return obj


def front_face(obj):
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    idx = [f.index for f in bm.faces if f.normal.y < -0.9][0]
    bm.free()
    return idx


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

        res = apply_feature(
            "floor", FloorOptions(floor_count=2, floor_height=3.0), FaceTarget(obj)
        )
        self.assertTrue(res.ok, res.errors)
        for group in ("walls", "roof", "slabs"):
            self.assertGreater(res.matgroup_counts.get(group, 0), 0, group)

        res = apply_feature(
            "roof",
            RoofOptions(type="HIP", height=1.0),
            FaceTarget(obj, [top_face(obj)]),
        )
        self.assertTrue(res.ok, res.errors)
        self.assertGreater(res.matgroup_counts.get("roof_hangs", 0), 0)

        res = apply_feature(
            "door", DoorOptions(), FaceTarget(obj, [ground_wall_face(obj)])
        )
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
            "floor",
            FloorOptions(),
            FaceTarget(obj, [top_face(obj), ground_wall_face(obj)]),
        )
        self.assertEqual(res.status, "cancelled")
        self.assertTrue(res.errors)

    def test_unknown_feature_raises(self):
        with self.assertRaises(ValueError):
            apply_feature("nonsense", None)


class TestWallElements(unittest.TestCase):
    """Elements applied to a bare wall: strips must stay WALLS and selection
    driven features (balcony) must actually build."""

    def setUp(self):
        clean_scene()
        self.obj = make_wall()

    def test_door_tags_wall_strips(self):
        # -- 5 untouched box faces + 2 side strips + 1 restored sliver = 8
        #    (pre-fix this was 7: a wall-plane face was tagged into the door)
        res = apply_feature(
            "door",
            DoorOptions(size_offset=SizeOffsetOptions(size=(1.5, 2.4))),
            FaceTarget(self.obj, [front_face(self.obj)]),
        )
        self.assertTrue(res.ok, res.errors)
        counts = res.matgroup_counts
        self.assertGreaterEqual(counts.get("walls", 0), 8)
        for group in ("door", "frame"):
            self.assertGreater(counts.get(group, 0), 0, group)

    def test_window_tags_wall_strips(self):
        # -- 5 untouched + 2 side strips + 1 restored = 8 (pre-fix: 7)
        res = apply_feature(
            "window",
            WindowOptions(size_offset=SizeOffsetOptions(size=(2.4, 1.6))),
            FaceTarget(self.obj, [front_face(self.obj)]),
        )
        self.assertTrue(res.ok, res.errors)
        counts = res.matgroup_counts
        self.assertGreaterEqual(counts.get("walls", 0), 7)
        for group in ("window", "frame"):
            self.assertGreater(counts.get(group, 0), 0, group)

    def test_balcony_builds_geometry(self):
        # -- regression: balcony used to no-op when nothing was 'selected'
        before = len(self.obj.data.polygons)
        res = apply_feature(
            "balcony",
            BalconyOptions(size_offset=SizeOffsetOptions(size=(5.0, 0.2))),
            FaceTarget(self.obj, [front_face(self.obj)]),
        )
        self.assertTrue(res.ok, res.errors)
        self.assertGreater(len(self.obj.data.polygons), before)
        self.assertGreater(res.matgroup_counts.get("balcony", 0), 0)


class TestPresets(unittest.TestCase):
    """Every bundled preset must build and satisfy the matgroup contract."""

    def test_all_presets_build_and_validate(self):
        # -- import through the addon's own namespace: its property groups
        #    are the ones registered by the harness
        from building_tools.btools.api.presets import PRESETS, build_preset

        for pid, preset in PRESETS.items():
            with self.subTest(preset=pid):
                clean_scene()
                res = build_preset(preset)
                self.assertTrue(res.ok, "%s: %s" % (pid, res.errors))
                obj = bpy.data.objects[res.created_object]
                report = validate_object(obj, include_geometry=False)
                self.assertTrue(report["ok"], "%s: %s" % (pid, report["problems"]))
                self.assertGreater(len(obj.data.polygons), 10, pid)


if __name__ == "__main__":
    unittest.main()

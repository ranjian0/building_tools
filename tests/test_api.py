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
from btools.api.presets import BuildingPreset, FacadeRule, build_preset
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


class TestPresetSeeds(unittest.TestCase):
    """Seeded randomization in build_preset (#163 seedian integration)."""

    @classmethod
    def setUpClass(cls):
        # -- ensure all property groups (and their pointer targets) exist
        import test_api_options

        test_api_options.register_all()

    def setUp(self):
        clean_scene()

    @staticmethod
    def _preset():
        return BuildingPreset(
            id="seed-test",
            label="Seed Test",
            floorplan={"type": "RECTANGULAR", "width": 8.0, "length": 6.0},
            floors={"floor_count": 2, "floor_height": 3.0},
            facade=[
                FacadeRule(
                    "window",
                    "front_walls",
                    (1,),
                    {"array": {"count": 2}, "size_offset": {"size": [1.2, 1.4]}},
                    variations={"fill_type": ["BAR", "GLASS_PANES"]},
                ),
                FacadeRule(
                    "window",
                    "side_walls",
                    (0, 1),
                    {"size_offset": {"size": [1.2, 1.4]}},
                    variations={"fill_type": ["BAR", "GLASS_PANES", "LOUVER"]},
                ),
            ],
        )

    def test_seed_reproducible(self):
        r1 = build_preset(self._preset(), seed="s1")
        r2 = build_preset(self._preset(), seed="s1")
        self.assertTrue(r1.ok, r1.errors)
        self.assertEqual(r1.matgroup_counts, r2.matgroup_counts)
        self.assertEqual(r1.decisions, r2.decisions)
        # -- one draw per matched face (1 front + 4 side)
        self.assertEqual(len(r1.decisions), 5)
        for path, decision, value in r1.decisions:
            self.assertEqual(decision, "choice")
            self.assertTrue(path.startswith("facade/window/"))
            self.assertIn(value, ("BAR", "GLASS_PANES", "LOUVER"))

    def test_seedless_has_no_decisions(self):
        r = build_preset(self._preset())
        self.assertTrue(r.ok, r.errors)
        self.assertEqual(r.decisions, [])


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
        #    (sill below adds an extra frame face, so >= 8 not == 9)
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


class TestOpeningDetails(unittest.TestCase):
    """Casing / hardware / sill detail options must build and tag cleanly."""

    def setUp(self):
        clean_scene()
        self.obj = make_wall()

    def _apply(self, feature, options):
        return apply_feature(
            feature, options, FaceTarget(self.obj, [front_face(self.obj)])
        )

    def test_door_hardware_adds_faces(self):
        plain = self._apply(
            "door", DoorOptions(size_offset=SizeOffsetOptions(size=(1.5, 2.4)))
        )
        self.assertTrue(plain.ok, plain.errors)
        with_hw = self._apply(
            "door",
            DoorOptions(
                size_offset=SizeOffsetOptions(size=(1.5, 2.4)), add_hardware=True
            ),
        )
        self.assertTrue(with_hw.ok, with_hw.errors)
        # rose (18 faces) + lever cube (6) live inside the door group
        self.assertGreater(
            with_hw.matgroup_counts.get("door", 0),
            plain.matgroup_counts.get("door", 0),
        )
        report = validate_object(
            self.obj, expect={"groups": ["door", "frame"]}, include_geometry=False
        )
        self.assertTrue(report["ok"], report["problems"])

    def test_door_bar_pull_style(self):
        res = self._apply(
            "door",
            DoorOptions(
                size_offset=SizeOffsetOptions(size=(1.5, 2.4)),
                add_hardware=True,
                handle_style="BAR_PULL",
            ),
        )
        self.assertTrue(res.ok, res.errors)
        self.assertGreater(res.matgroup_counts.get("door", 0), 0)

    def test_door_casing_builds(self):
        res = self._apply(
            "door",
            DoorOptions(
                size_offset=SizeOffsetOptions(size=(1.5, 2.4)), add_casing=True
            ),
        )
        self.assertTrue(res.ok, res.errors)
        report = validate_object(
            self.obj, expect={"groups": ["door", "frame"]}, include_geometry=False
        )
        self.assertTrue(report["ok"], report["problems"])

    def test_window_casing_builds(self):
        res = self._apply(
            "window",
            WindowOptions(
                size_offset=SizeOffsetOptions(size=(2.4, 1.6)), add_casing=True
            ),
        )
        self.assertTrue(res.ok, res.errors)
        report = validate_object(
            self.obj, expect={"groups": ["window", "frame"]}, include_geometry=False
        )
        self.assertTrue(report["ok"], report["problems"])

    def test_window_sill_proud_of_wall(self):
        res = self._apply(
            "window", WindowOptions(size_offset=SizeOffsetOptions(size=(2.4, 1.6)))
        )
        self.assertTrue(res.ok, res.errors)
        # sill projects past the wall face plane (front face at y = -0.2)
        front_y = min(v.co.y for v in self.obj.data.vertices)
        self.assertLess(front_y, -0.2 - 1e-6)


class TestPresets(unittest.TestCase):
    """Every bundled preset must build and satisfy the matgroup contract."""

    @unittest.skipIf(
        bpy.app.background,
        "preset composition needs the full session context; "
        "verified via just test-blender and the reference corpus",
    )
    def test_all_presets_build_and_validate(self):
        import importlib

        addon = self._addon_module()
        presets_mod = importlib.import_module(addon.__name__ + ".btools.api.presets")
        PRESETS = presets_mod.PRESETS
        build_preset = presets_mod.build_preset

        for pid, preset in PRESETS.items():
            with self.subTest(preset=pid):
                clean_scene()
                res = build_preset(preset)
                if not res.ok:
                    tb = res.errors[1] if len(res.errors) > 1 else ""
                    frames = [
                        ln.strip()
                        for ln in tb.splitlines()
                        if ln.strip().startswith("File ")
                    ]
                    self.fail(
                        "%s failed: %s ||| FRAMES: %s"
                        % (pid, res.errors[0], " >> ".join(frames[-4:]))
                    )
                obj = bpy.data.objects[res.created_object]
                report = validate_object(obj, include_geometry=False)
                self.assertTrue(report["ok"], "%s: %s" % (pid, report["problems"]))
                self.assertGreater(len(obj.data.polygons), 10, pid)


if __name__ == "__main__":
    unittest.main()


class TestFrameBevels(unittest.TestCase):
    """add_bevel: bevel-after-fill keeps the matgroup contract."""

    def setUp(self):
        clean_scene()

    def test_window_bevel(self):
        obj = make_wall()
        before = apply_feature(
            "window",
            WindowOptions(
                size_offset=SizeOffsetOptions(size=(2.0, 1.6)),
                fill_type="GLASS_PANES",
            ),
            FaceTarget(obj, [front_face(obj)]),
        )
        self.assertTrue(before.ok, before.errors)
        plain_edges = len(obj.data.edges)

        clean_scene()
        obj2 = make_wall()
        after = apply_feature(
            "window",
            WindowOptions(
                size_offset=SizeOffsetOptions(size=(2.0, 1.6)),
                fill_type="GLASS_PANES",
                add_bevel=True,
                bevel_width=0.004,
            ),
            FaceTarget(obj2, [front_face(obj2)]),
        )
        self.assertTrue(after.ok, after.errors)
        # bevel adds chamfer faces -> more edges than the plain build
        self.assertGreater(len(obj2.data.edges), plain_edges)
        report = validate_object(obj2, include_geometry=False)
        self.assertTrue(report["ok"], report["problems"])

    def test_default_off_is_plain(self):
        clean_scene()
        plain = make_wall()
        r = apply_feature(
            "window",
            WindowOptions(size_offset=SizeOffsetOptions(size=(2.0, 1.6))),
            FaceTarget(plain, [front_face(plain)]),
        )
        self.assertTrue(r.ok, r.errors)
        self.assertFalse(r.warnings)

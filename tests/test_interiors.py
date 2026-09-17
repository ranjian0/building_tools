"""Tests for phase-1 interiors: double-shell walls (#202, roadmap item 7)."""

import unittest

import bpy

from btools.api import FaceTarget, FloorOptions, FloorplanOptions, apply_feature
from btools.api.validate import validate_object


def clean_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)


def build(floor_kwargs, width=10.0, length=8.0):
    res = apply_feature("floorplan", FloorplanOptions(width=width, length=length))
    obj = bpy.data.objects[res.created_object]
    res = apply_feature("floor", FloorOptions(**floor_kwargs), FaceTarget(obj))
    return obj, res


def group_faces(obj, group):
    attr = obj.data.attributes.get(".bt_material_group_index")
    if attr is None:
        return []
    names = [mt.name for mt in getattr(obj, "bt_materials", [])]
    if group not in names:
        return []
    gi = names.index(group)
    vals = [0] * len(obj.data.polygons)
    attr.data.foreach_get("value", vals)
    return [p for p, tag in zip(obj.data.polygons, vals) if tag == gi]


class TestRuleContextInterior(unittest.TestCase):
    """ctx.interior after a roof must find the upward slab face (#218-class).

    _ground_floor_face used to ignore face orientation and could hand the
    interior op a vertical slab-band side face (watchtower example)."""

    def test_interior_after_roof(self):
        import btools

        btools.ensure_registered()
        clean_scene()
        import btools.rules as rules_mod

        ctx = rules_mod.RuleContext()
        ctx.floorplan(type="RECTANGULAR", width=6.0, length=6.0)
        ctx.floors(floor_count=2, floor_height=5.0)
        ctx.roof(type="HIP", height=2.0, outset=0.6)
        res = ctx.interior(partition_mode="SKELETON", min_corridor=2.0)
        self.assertEqual(res.status, "ok", res.errors[:1])
        # partitions are tagged into the walls group; the skeleton core
        # adds interior faces beyond the 4 outer wall faces
        self.assertGreater(res.matgroup_counts.get("walls", 0), 4)


class TestInteriorShell(unittest.TestCase):
    def setUp(self):
        clean_scene()

    def test_thickness_zero_regression(self):
        # -- 0 keeps the single skin: counts identical to a plain build
        plain_obj, plain = build({"floor_count": 2, "floor_height": 3.0})
        thick0_obj, thick0 = build(
            {"floor_count": 2, "floor_height": 3.0, "wall_thickness": 0.0}
        )
        self.assertTrue(plain.ok and thick0.ok)
        self.assertEqual(
            plain.matgroup_counts.get("walls"), thick0.matgroup_counts.get("walls")
        )
        self.assertEqual(
            plain.matgroup_counts.get("slabs"), thick0.matgroup_counts.get("slabs")
        )

    def test_double_shell_rectangular(self):
        obj, res = build({"floor_count": 2, "floor_height": 3.0, "wall_thickness": 0.2})
        self.assertTrue(res.ok, res.errors)
        report = validate_object(obj, expect={"groups": ["walls", "slabs"]})
        self.assertTrue(report["ok"], report["problems"])

        counts = res.matgroup_counts
        # -- inner tube: 4 faces per storey (rectangular offset ring)
        self.assertGreaterEqual(counts.get("walls", 0), 8)
        # -- one full-width interior floor per storey
        self.assertGreaterEqual(counts.get("slabs", 0), 2)

        # -- the interior floor spans the full footprint at storey bases
        floors = [p for p in group_faces(obj, "slabs") if abs(p.area - 80.0) < 1e-3]
        self.assertEqual(len(floors), 2)
        for f in floors:
            self.assertTrue(
                abs(f.center.z - 0.2) < 1e-3 or abs(f.center.z - 3.4) < 1e-3
            )

        # -- inner wall skin: a walls face offset 0.2 inside the x=+5
        #    wall, facing the room (normal points inward)
        inner_x = [
            p
            for p in group_faces(obj, "walls")
            if abs(p.center.x - 4.8) < 1e-3 and p.normal.x < -0.9
        ]
        self.assertTrue(inner_x)

    def test_double_shell_no_slabs(self):
        obj, res = build(
            {
                "floor_count": 2,
                "floor_height": 3.0,
                "add_slab": False,
                "wall_thickness": 0.15,
            }
        )
        self.assertTrue(res.ok, res.errors)
        report = validate_object(obj, include_geometry=False)
        self.assertTrue(report["ok"], report["problems"])
        # -- interior floors at z = 0 and z = 3 (no slab offset)
        floors = [
            p
            for p in group_faces(obj, "slabs")
            if abs(p.area - 80.0) < 1e-3
            and (abs(p.center.z) < 1e-3 or abs(p.center.z - 3.0) < 1e-3)
        ]
        self.assertEqual(len(floors), 2)

    def test_double_shell_l_shape(self):
        res0 = apply_feature(
            "floorplan",
            FloorplanOptions(type="H-SHAPED", width=12.0, length=12.0),
        )
        obj = bpy.data.objects[res0.created_object]
        res = apply_feature(
            "floor",
            FloorOptions(floor_count=2, floor_height=3.0, wall_thickness=0.2),
            FaceTarget(obj),
        )
        self.assertTrue(res.ok, res.errors)
        report = validate_object(obj, include_geometry=False)
        self.assertTrue(report["ok"], report["problems"])

    def test_too_thick_falls_back_gracefully(self):
        # -- offset beyond the footprint: no interior, build still valid
        obj, res = build(
            {"floor_count": 1, "floor_height": 3.0, "wall_thickness": 8.0},
            width=6.0,
            length=4.0,
        )
        self.assertTrue(res.ok, res.errors)
        report = validate_object(obj, include_geometry=False)
        self.assertTrue(report["ok"], report["problems"])

    def test_roof_still_applies(self):
        # -- the top face must survive the interior pass for roofs
        from btools.api import RoofOptions
        from btools.api.select import select

        obj, res = build({"floor_count": 2, "floor_height": 3.0, "wall_thickness": 0.2})
        r = apply_feature(
            "roof",
            RoofOptions(type="HIP", slope_mode="ANGLE", slope_angle=0.6),
            FaceTarget(obj, select(obj, "top_face")),
        )
        self.assertTrue(r.ok, r.errors)
        self.assertGreater(r.matgroup_counts.get("roof", 0), 0)
        report = validate_object(obj, include_geometry=False)
        self.assertTrue(report["ok"], report["problems"])


if __name__ == "__main__":
    unittest.main()


class TestCornice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_api_options

        test_api_options.register_all()

    def setUp(self):
        clean_scene()

    def test_cornice_projects_past_slab(self):
        from btools.api import FaceTarget, FloorOptions, FloorplanOptions, apply_feature

        res = apply_feature("floorplan", FloorplanOptions(width=10.0, length=8.0))
        obj = bpy.data.objects[res.created_object]
        res = apply_feature(
            "floor",
            FloorOptions(
                floor_count=2,
                floor_height=3.0,
                add_cornice=True,
                cornice_size=0.15,
            ),
            FaceTarget(obj),
        )
        self.assertTrue(res.ok, res.errors)
        # walls at +-5.0, slab outset 0.1, cornice +0.15 -> extent 5.25
        xs = max(v.co.x for v in obj.data.vertices)
        self.assertAlmostEqual(xs, 5.25, delta=0.02)
        report = validate_object(obj, include_geometry=False)
        self.assertTrue(report["ok"], report["problems"])

    def test_no_cornice_by_default(self):
        from btools.api import FaceTarget, FloorOptions, FloorplanOptions, apply_feature

        res = apply_feature("floorplan", FloorplanOptions(width=10.0, length=8.0))
        obj = bpy.data.objects[res.created_object]
        apply_feature(
            "floor", FloorOptions(floor_count=2, floor_height=3.0), FaceTarget(obj)
        )
        # extent = walls + slab outset only (5.1)
        xs = max(v.co.x for v in obj.data.vertices)
        self.assertAlmostEqual(xs, 5.1, delta=0.02)


class TestDetailLevel(unittest.TestCase):
    def test_flag_table(self):
        import btools.utils.detail as detail

        # LOW forces silhouette extras off regardless of user value
        self.assertFalse(detail.detail_flag("gutters", "LOW", True))
        self.assertFalse(detail.detail_flag("cornice", "LOW", True))
        self.assertFalse(detail.detail_flag("chimney", "LOW", True))
        # MEDIUM keeps the user's value
        self.assertTrue(detail.detail_flag("gutters", "MEDIUM", True))
        self.assertFalse(detail.detail_flag("gutters", "MEDIUM", False))
        self.assertIsNone(detail.detail_flag("gutters", "MEDIUM", None))
        # HIGH forces casings on
        self.assertTrue(detail.detail_flag("casing", "HIGH", False))
        # unknown features pass through
        self.assertTrue(detail.detail_flag("spandrels", "LOW", True))

    def test_scene_property_roundtrip(self):
        import bpy

        import btools.utils.detail as detail

        detail.register()
        try:
            scene = bpy.context.scene
            scene.btools_detail_level = "HIGH"
            self.assertEqual(detail.detail_level(), "HIGH")
            scene.btools_detail_level = "LOW"
            self.assertEqual(detail.detail_level(), "LOW")
            scene.btools_detail_level = "MEDIUM"
        finally:
            detail.unregister()


class TestColumnDetails(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_api_options

        test_api_options.register_all()

    def setUp(self):
        clean_scene()

    def test_base_and_capital(self):
        from btools.api import FaceTarget, FloorOptions, FloorplanOptions, apply_feature

        res = apply_feature("floorplan", FloorplanOptions(width=10.0, length=8.0))
        obj = bpy.data.objects[res.created_object]
        res = apply_feature(
            "floor",
            FloorOptions(
                floor_count=1,
                floor_height=3.0,
                add_columns=True,
                add_column_base=True,
                add_column_capital=True,
                column_size=0.3,
                column_cap_size=1.5,
                column_cap_height=0.1,
            ),
            FaceTarget(obj),
        )
        self.assertTrue(res.ok, res.errors)
        self.assertGreater(res.matgroup_counts.get("columns", 0), 0)
        # cap blocks are wider than the shaft: x extent of columns grows
        # beyond the corner + size/2 (0.15) to + cap_w/2 (0.225)
        col_x = max(
            v.co.x
            for v in obj.data.vertices
            if abs(v.co.x - 5.0) < 0.5  # near the +x corners
        )
        self.assertGreater(col_x, 5.15)
        report = validate_object(obj, include_geometry=False)
        self.assertTrue(report["ok"], report["problems"])

    def test_column_size_decoupled(self):
        from btools.api import FaceTarget, FloorOptions, FloorplanOptions, apply_feature

        res = apply_feature("floorplan", FloorplanOptions(width=10.0, length=8.0))
        obj = bpy.data.objects[res.created_object]
        res = apply_feature(
            "floor",
            FloorOptions(
                floor_count=1,
                floor_height=3.0,
                add_columns=True,
                column_size=0.2,  # slab_outset is 0.1 -> default col 0.2
            ),
            FaceTarget(obj),
        )
        self.assertTrue(res.ok, res.errors)
        self.assertGreater(res.matgroup_counts.get("columns", 0), 0)


class TestFakeInteriors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_api_options

        test_api_options.register_all()

    def setUp(self):
        clean_scene()

    def test_material_swap(self):
        import bpy

        from btools.api import FaceTarget, FloorOptions, FloorplanOptions, apply_feature
        from btools.building.default_materials import (
            apply_default_materials,
            apply_fake_interiors,
        )

        res = apply_feature("floorplan", FloorplanOptions(width=8.0, length=6.0))
        obj = bpy.data.objects[res.created_object]
        apply_feature(
            "floor", FloorOptions(floor_count=1, floor_height=3.0), FaceTarget(obj)
        )
        # simulate a windowed build: slot names are what the swap keys on
        # (placing a live window here is namespace-fragile in the harness)
        from btools.building.default_materials import _material

        apply_default_materials(obj)
        obj.data.materials.append(_material("BT_window"))
        obj.data.materials.append(_material("BT_window_panes"))
        before = {
            m.name for m in obj.data.materials if m and m.name.startswith("BT_window")
        }
        if not before:
            print(
                "DEBUG no window mats; all:",
                [m.name for m in obj.data.materials if m],
                "faces:",
                faces,
            )
        self.assertTrue(before)

        swapped = apply_fake_interiors(obj, enable=True)
        self.assertGreater(swapped, 0)
        now = {m.name for m in obj.data.materials if m}
        self.assertIn("BT_window_fake_interior", now)
        # the variant material exists with an emission node
        mat = bpy.data.materials.get("BT_window_fake_interior")
        self.assertIsNotNone(mat)
        self.assertTrue(any(n.type == "EMISSION" for n in mat.node_tree.nodes))
        # swapping back restores the standard materials
        apply_fake_interiors(obj, enable=False)
        restored = {m.name for m in obj.data.materials if m}
        self.assertIn("BT_walls", restored)

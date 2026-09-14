"""Headless tests for slope-driven roofs (#208) and the flat-top roof type."""

import math
import unittest

import bmesh
import bpy

from btools.api import FaceTarget, RoofOptions, apply_feature
from btools.api.validate import validate_object


def clean_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)


def make_footprint(width, length):
    """Bare upward-facing rectangle at z=0 (no floorplan feature needed)."""
    me = bpy.data.meshes.new("fp_mesh")
    obj = bpy.data.objects.new("fp", me)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    hw, hl = width / 2.0, length / 2.0
    verts = [
        bm.verts.new((-hw, -hl, 0.0)),
        bm.verts.new((hw, -hl, 0.0)),
        bm.verts.new((hw, hl, 0.0)),
        bm.verts.new((-hw, hl, 0.0)),
    ]
    bm.faces.new(verts)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    return obj


def build_roof(width, length, **roof_kwargs):
    """Footprint -> roof on its face; returns (obj, OpResult)."""
    obj = make_footprint(width, length)
    res = apply_feature("roof", RoofOptions(**roof_kwargs), FaceTarget(obj, [0]))
    return obj, res


def group_faces(obj, group):
    """Mesh polygons tagged to a material group."""
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


def group_z_delta(obj, group):
    """(max - min) Z over a group's vertices: the group's own height."""
    zs = [
        obj.data.vertices[i].co.z for p in group_faces(obj, group) for i in p.vertices
    ]
    return max(zs) - min(zs) if zs else None


class TestRoofSlopeModes(unittest.TestCase):
    """Slope modes on a 10x10 footprint with outset 0.1 (skeleton polygon
    10.2 x 10.2, inradius 5.1); deltas are measured within the roof group so
    the hang base/thickness cancels out."""

    RISE = 5.1  # inradius of the outset square

    def setUp(self):
        clean_scene()

    def test_height_mode_regression(self):
        # -- HEIGHT: tallest arc reaches prop.height (pre-existing behavior)
        obj, res = build_roof(10, 10, type="HIP", height=2.0)
        self.assertTrue(res.ok, res.errors)
        self.assertAlmostEqual(group_z_delta(obj, "roof"), 2.0, places=4)

    def test_angle_mode(self):
        # -- tan(45deg) = 1: rise equals the inradius
        obj, res = build_roof(
            10, 10, type="HIP", slope_mode="ANGLE", slope_angle=math.radians(45.0)
        )
        self.assertTrue(res.ok, res.errors)
        self.assertAlmostEqual(group_z_delta(obj, "roof"), self.RISE, places=3)
        report = validate_object(obj, expect={"groups": ["roof", "roof_hangs"]})
        self.assertTrue(report["ok"], report["problems"])

    def test_percentage_mode(self):
        # -- 50% slope: rise = inradius * 0.5
        obj, res = build_roof(
            10, 10, type="HIP", slope_mode="PERCENTAGE", slope_percentage=50.0
        )
        self.assertTrue(res.ok, res.errors)
        self.assertAlmostEqual(group_z_delta(obj, "roof"), self.RISE * 0.5, places=3)

    def test_percentage_half_of_hundred(self):
        obj50, _ = build_roof(
            10, 10, type="HIP", slope_mode="PERCENTAGE", slope_percentage=50.0
        )
        obj100, _ = build_roof(
            10, 10, type="HIP", slope_mode="PERCENTAGE", slope_percentage=100.0
        )
        self.assertAlmostEqual(
            group_z_delta(obj50, "roof") * 2.0, group_z_delta(obj100, "roof"), places=3
        )

    def test_gable_angle_mode(self):
        # -- open gable on 10x20: ridge rises half the 10 span at 45deg
        obj, res = build_roof(
            10,
            20,
            type="GABLE",
            slope_mode="ANGLE",
            slope_angle=math.radians(45.0),
            add_ridge_cap=False,
        )
        self.assertTrue(res.ok, res.errors)
        # -- 5.0 rise + the gable finisher's thickness extrusion (0.1) and
        #    outset dip (outset/2 = 0.05) on the raking edges
        self.assertAlmostEqual(group_z_delta(obj, "roof"), 5.05, places=2)


class TestFlatTopRoof(unittest.TestCase):
    RISE = 5.1  # inradius of the outset square (outset 0.1)

    def setUp(self):
        clean_scene()

    def _flat_cap_faces(self, obj):
        return [p for p in group_faces(obj, "roof") if p.normal.z > 0.99]

    def test_flat_top_cap(self):
        # -- square hip truncated at 2m with 45deg pitch below the cap
        obj, res = build_roof(
            10,
            10,
            type="FLAT_TOP",
            slope_mode="ANGLE",
            slope_angle=math.radians(45.0),
            flat_height=2.0,
        )
        self.assertTrue(res.ok, res.errors)
        self.assertAlmostEqual(group_z_delta(obj, "roof"), 2.0, places=3)

        # -- a flat cap face exists at the truncation height, sized by the
        #    level-set inset (cap/tan) from the outset square
        caps = self._flat_cap_faces(obj)
        self.assertGreaterEqual(len(caps), 1)
        expected_area = (10 + 2 * 0.1 - 2 * 2.0) ** 2
        total = sum(f.area for f in caps)
        self.assertAlmostEqual(total, expected_area, delta=0.05)

        report = validate_object(obj, expect={"groups": ["roof", "roof_hangs"]})
        self.assertTrue(report["ok"], report["problems"])

    def test_flat_top_above_apex_falls_back(self):
        # -- flat_height above the apex: nothing to truncate, full hip
        obj, res = build_roof(
            10,
            10,
            type="FLAT_TOP",
            slope_mode="ANGLE",
            slope_angle=math.radians(45.0),
            flat_height=9.0,
        )
        self.assertTrue(res.ok, res.errors)
        self.assertAlmostEqual(group_z_delta(obj, "roof"), self.RISE, places=3)
        report = validate_object(obj, expect={"groups": ["roof", "roof_hangs"]})
        self.assertTrue(report["ok"], report["problems"])

    def test_flat_top_rectangle_two_peaks(self):
        # -- 20x10 rectangle: two ridge peaks; a low cap merges them into one ring
        obj, res = build_roof(
            20,
            10,
            type="FLAT_TOP",
            slope_mode="ANGLE",
            slope_angle=math.radians(45.0),
            flat_height=2.0,
        )
        self.assertTrue(res.ok, res.errors)
        self.assertAlmostEqual(group_z_delta(obj, "roof"), 2.0, places=3)
        report = validate_object(obj, expect={"groups": ["roof", "roof_hangs"]})
        self.assertTrue(report["ok"], report["problems"])


class TestMansardRoof(unittest.TestCase):
    def setUp(self):
        clean_scene()

    def _roof_group_zs(self, obj):
        zs = [
            obj.data.vertices[i].co.z
            for p in group_faces(obj, "roof")
            for i in p.vertices
        ]
        return sorted(round(z, 4) for z in zs)

    def test_mansard_two_tiers(self):
        # -- 45deg lower band to a 2m break, 1m hip tier above it
        obj, res = build_roof(
            10,
            10,
            type="MANSARD",
            slope_mode="ANGLE",
            slope_angle=math.radians(45.0),
            lower_height=2.0,
            upper_height=1.0,
        )
        self.assertTrue(res.ok, res.errors)
        # -- eave 0.1 + 2.0 break + 1.0 apex = 3.1 total rise
        self.assertAlmostEqual(group_z_delta(obj, "roof"), 3.0, places=3)
        zs = self._roof_group_zs(obj)
        self.assertIn(2.1, zs)  # break ring
        self.assertAlmostEqual(zs[-1], 3.1, places=3)  # apex
        # -- square: 4 lower trapezoids + 4 upper slopes
        self.assertEqual(len(group_faces(obj, "roof")), 8)
        report = validate_object(obj, expect={"groups": ["roof", "roof_hangs"]})
        self.assertTrue(report["ok"], report["problems"])

    def test_mansard_break_above_apex_falls_back(self):
        # -- lower_height above the apex: no break, plain full hip
        obj, res = build_roof(
            10,
            10,
            type="MANSARD",
            slope_mode="ANGLE",
            slope_angle=math.radians(45.0),
            lower_height=9.0,
            upper_height=1.0,
        )
        self.assertTrue(res.ok, res.errors)
        self.assertAlmostEqual(group_z_delta(obj, "roof"), 5.1, places=3)
        report = validate_object(obj, expect={"groups": ["roof", "roof_hangs"]})
        self.assertTrue(report["ok"], report["problems"])

    def test_mansard_rectangle(self):
        obj, res = build_roof(
            20,
            10,
            type="MANSARD",
            slope_mode="ANGLE",
            slope_angle=math.radians(60.0),
            lower_height=2.6,
            upper_height=0.8,
        )
        self.assertTrue(res.ok, res.errors)
        self.assertAlmostEqual(group_z_delta(obj, "roof"), 3.4, places=2)
        report = validate_object(obj, expect={"groups": ["roof", "roof_hangs"]})
        self.assertTrue(report["ok"], report["problems"])


if __name__ == "__main__":
    unittest.main()

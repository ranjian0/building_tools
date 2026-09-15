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

"""Headless tests for the probe/checks validation layer."""

import unittest

import bpy
import bmesh
from mathutils import Vector

from btools.api import (
    DoorOptions,
    FaceTarget,
    FloorOptions,
    FloorplanOptions,
    SizeOffsetOptions,
    WindowOptions,
    apply_feature,
    elevation_bays,
    group_intersections,
    group_protrusions,
    measure_object,
    run_checks,
    storey_bands,
)
from btools.api.probe import ascii_elevation, counts_per_storey


def front_face(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    idx = [f.index for f in bm.faces if f.normal.y < -0.9][0]
    bm.free()
    return idx


def make_wall():
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


def make_overlapping_boxes(obj_name="overlap"):
    """Two interpenetrating cubes in one mesh, tagged into 2 matgroups."""
    me = bpy.data.meshes.new(obj_name + "_mesh")
    obj = bpy.data.objects.new(obj_name, me)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((-0.3, 0.1, 0.0)))
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.translate(bm, verts=bm.verts[-8:], vec=Vector((0.3, -0.1, 0.2)))
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()

    # tag: first 6 faces group 0, last 6 group 1
    attr = me.attributes.new(".bt_material_group_index", "INT", "FACE")
    for i, p in enumerate(me.polygons):
        p.select = i < 6
    vals = [0 if i < 6 else 1 for i in range(len(me.polygons))]
    attr.data.foreach_set("value", vals)
    me.update()

    if hasattr(obj, "bt_materials"):
        for name in ("aaa", "bbb"):
            mt = obj.bt_materials.add()
            mt.name = name
    return obj


class TestProbes(unittest.TestCase):
    def setUp(self):
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)

    def test_storey_bands_from_slabs(self):
        res = apply_feature("floorplan", FloorplanOptions(width=8, length=6))
        obj = bpy.data.objects[res.created_object]
        apply_feature(
            "floor", FloorOptions(floor_count=2, floor_height=3.0), FaceTarget(obj)
        )
        bands = storey_bands(obj)
        self.assertEqual(len(bands), 2)
        self.assertLess(bands[0]["z"], bands[1]["z"])

    def test_window_bays_and_sill_protrusion(self):
        obj = make_wall()
        res = apply_feature(
            "window",
            WindowOptions(size_offset=SizeOffsetOptions(size=(2.0, 1.6))),
            FaceTarget(obj, [front_face(obj)]),
        )
        self.assertTrue(res.ok, res.errors)

        bays = elevation_bays(obj, "window", view="front")
        self.assertEqual(len(bays), 1)
        self.assertAlmostEqual(bays[0]["center"], 0.0, delta=0.1)
        self.assertAlmostEqual(bays[0]["z_max"] - bays[0]["z_min"], 1.6, delta=0.15)

        protr = group_protrusions(obj, "frame")
        front = [p for p in protr if p["normal"][1] < -0.9]  # viewer-facing
        self.assertTrue(front, protr)
        # sill lip past the wall plane: 75mm projection from the
        # 50mm-recessed frame = ~25mm visible
        self.assertGreater(front[0]["protrusion"], 0.02)

    def test_ascii_elevation(self):
        obj = make_wall()
        apply_feature(
            "window",
            WindowOptions(size_offset=SizeOffsetOptions(size=(2.0, 1.6))),
            FaceTarget(obj, [front_face(obj)]),
        )
        text = ascii_elevation(obj, view="front", width=80, height=30)
        lines = text.splitlines()
        self.assertEqual(len(lines), 32)  # 30 grid + meta + legend
        self.assertTrue(all(len(l) == 80 for l in lines[:30]))
        self.assertIn("view=front", lines[30])
        # the window group char must appear somewhere in the grid
        legend = lines[31]
        win_char = [c for c in legend.split() if c.endswith("=window")]
        self.assertTrue(win_char, legend)
        grid = "\n".join(lines[:30])
        self.assertIn(win_char[0][0], grid)

    def test_group_intersections_detects_interpenetration(self):
        obj = make_overlapping_boxes()
        self.assertGreater(group_intersections(obj, "aaa", "bbb"), 0)
        self.assertGreater(group_intersections(obj, "bbb", "aaa"), 0)
        report = measure_object(obj)
        self.assertIn("counts", report)

    def test_touching_boxes_do_not_intersect(self):
        """Coplanar touching is not interpenetration (posts on platforms)."""
        import bmesh

        me = bpy.data.meshes.new("touch_mesh")
        obj = bpy.data.objects.new("touch", me)
        bpy.context.scene.collection.objects.link(obj)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((0, 0, 0.5)))
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.translate(bm, verts=bm.verts[-8:], vec=Vector((0, 0, 1.5)))
        bm.normal_update()
        bm.to_mesh(me)
        bm.free()
        attr = me.attributes.new(".bt_material_group_index", "INT", "FACE")
        attr.data.foreach_set("value", [0] * 6 + [1] * 6)
        me.update()
        if hasattr(obj, "bt_materials"):
            for name in ("aaa", "bbb"):
                mt = obj.bt_materials.add()
                mt.name = name
        self.assertEqual(group_intersections(obj, "aaa", "bbb"), 0)
        self.assertEqual(group_intersections(obj, "bbb", "aaa"), 0)

    def test_counts_per_storey(self):
        res = apply_feature("floorplan", FloorplanOptions(width=8, length=6))
        obj = bpy.data.objects[res.created_object]
        apply_feature(
            "floor", FloorOptions(floor_count=2, floor_height=3.0), FaceTarget(obj)
        )
        counts = counts_per_storey(obj, "walls")
        self.assertEqual(sorted(counts), ["storey_0", "storey_1"])
        self.assertGreater(counts["storey_0"], 0)


class TestCheckRunner(unittest.TestCase):
    def setUp(self):
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)

    def test_group_present_pass_and_fail(self):
        obj = make_wall()
        apply_feature(
            "window",
            WindowOptions(size_offset=SizeOffsetOptions(size=(2.0, 1.6))),
            FaceTarget(obj, [front_face(obj)]),
        )
        good = run_checks(
            obj, [{"kind": "group_present", "groups": ["walls", "frame"]}]
        )
        self.assertTrue(good["ok"], good)
        bad = run_checks(obj, [{"kind": "group_present", "groups": ["balcony"]}])
        self.assertFalse(bad["ok"])
        self.assertIn("missing", bad["results"][0]["detail"])

    def test_xfail_does_not_fail_run(self):
        obj = make_wall()
        rep = run_checks(
            obj,
            [
                {
                    "kind": "group_present",
                    "groups": ["nonexistent"],
                    "xfail": True,
                    "reason": "known",
                }
            ],
        )
        self.assertTrue(rep["ok"])
        self.assertTrue(rep["results"][0]["xfail"])

    def test_unknown_kind_fails(self):
        obj = make_wall()
        rep = run_checks(obj, [{"kind": "nonsense"}])
        self.assertFalse(rep["ok"])
        self.assertIn("unknown kind", rep["results"][0]["detail"]["error"])

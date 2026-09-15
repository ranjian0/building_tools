"""Tests for batch generation from footprint attributes (item 8; #214/#173)."""

import unittest

import btools
from btools.api import (
    BatchOptions,
    batch_summary,
    generate_batch,
    resolve_building_plan,
    resolve_roof_type,
)


class TestResolveRoofType(unittest.TestCase):
    def test_osm_vocabulary(self):
        cases = [
            ("flat", "FLAT", None),
            ("gabled", "GABLE", None),
            ("pitched", "GABLE", None),
            ("crosspitched", "GABLE", None),
            ("hipped", "HIP", None),
            ("pyramidal", "HIP", None),
            ("half-hipped", "HALF_HIP", None),
            ("side_hipped", "HALF_HIP", None),
            ("hipped-and-gabled", "HALF_HIP", None),
            ("mansard", "MANSARD", None),
            ("Gabled", "GABLE", None),  # case-insensitive
        ]
        for value, want_type, _ in cases:
            got, warn = resolve_roof_type(value)
            self.assertEqual(got, want_type, value)
            self.assertIsNone(warn, value)

    def test_fallbacks_warn(self):
        for value in ("skillion", "onion", "dome", "round", "sawtooth"):
            got, warn = resolve_roof_type(value)
            self.assertEqual(got, "FLAT", value)
            self.assertTrue(warn, value)

    def test_missing(self):
        self.assertEqual(resolve_roof_type(None), (None, None))
        self.assertEqual(resolve_roof_type(""), (None, None))


class TestResolveBuildingPlan(unittest.TestCase):
    def test_levels_win_over_height(self):
        floors, roof, warns = resolve_building_plan(
            {"building:levels": 3, "height": 20.0}
        )
        self.assertEqual(floors["floor_count"], 3)
        self.assertEqual(warns, [])

    def test_height_derives_levels(self):
        floors, roof, _ = resolve_building_plan({"height": 9.5})
        self.assertEqual(floors["floor_count"], 3)  # 9.5 // 3.0

    def test_defaults(self):
        floors, roof, _ = resolve_building_plan({})
        self.assertEqual(floors["floor_count"], 2)
        self.assertAlmostEqual(floors["floor_height"], 3.0)
        self.assertEqual(roof["type"], "HIP")

    def test_roof_angle_over_height(self):
        import math

        _, roof, _ = resolve_building_plan({"roof:angle": 35.0, "roof:height": 2.0})
        self.assertEqual(roof.get("slope_mode"), "ANGLE")
        self.assertAlmostEqual(roof["slope_angle"], math.radians(35.0), places=6)
        self.assertEqual(roof["height"], 1.0)  # angle mode ignores absolute height

    def test_roof_height_only(self):
        _, roof, _ = resolve_building_plan({"roof:height": 1.8})
        self.assertEqual(roof["height"], 1.8)
        self.assertIsNone(roof.get("slope_mode"))

    def test_custom_attr_names(self):
        opts = BatchOptions(
            roof_type_attr="Roof Form",
            height_attr="EaveHeight",
        )
        floors, roof, _ = resolve_building_plan(
            {"Roof Form": "gable", "EaveHeight": 6.0}, opts
        )
        self.assertEqual(roof["type"], "GABLE")
        self.assertEqual(floors["floor_count"], 2)


class TestGenerateBatch(unittest.TestCase):
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
    def _footprint(name, x, props=None, w=8.0, l=6.0, lift=0.0):
        import bmesh
        import bpy

        me = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        bm = bmesh.new()
        hw, hl = w / 2, l / 2
        vs = [
            bm.verts.new((x - hw, -hl, lift)),
            bm.verts.new((x + hw, -hl, lift)),
            bm.verts.new((x + hw, hl, lift)),
            bm.verts.new((x - hw, hl, lift)),
        ]
        bm.faces.new(vs)
        bm.normal_update()
        bm.to_mesh(me)
        bm.free()
        for k, v in (props or {}).items():
            obj[k] = v
        return obj

    @staticmethod
    def _storey_count(obj):
        from btools.api import probe

        bands = probe.storey_bands(obj)
        return len(bands)

    def test_mixed_batch(self):
        import bpy

        foots = [
            self._footprint(
                "a_gable", -30, {"roof:shape": "gabled", "building:levels": 3}
            ),
            self._footprint("b_flat", -10, {"roof:shape": "flat", "height": 7.0}),
            self._footprint(
                "c_angle", 10, {"roof:shape": "hipped", "roof:angle": 45.0}
            ),
            self._footprint("d_bare", 30, {}),
            self._footprint("e_fallback", 50, {"roof:shape": "onion"}),
        ]
        results = generate_batch(foots)
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertTrue(r.ok, (r.object_name, r.errors[:1]))

        # footprints kept intact, buildings created alongside
        for f in foots:
            self.assertIn(f.name, bpy.data.objects)
            self.assertIn(f.name + "_bld", bpy.data.objects)

        # per-object plans
        a = bpy.data.objects["a_gable_bld"]
        self.assertEqual(self._storey_count(a), 3)
        b = bpy.data.objects["b_flat_bld"]
        self.assertEqual(self._storey_count(b), 2)  # 7 // 3
        c = bpy.data.objects["c_angle_bld"]
        e = [r for r in results if r.object_name == "e_fallback"][0]
        self.assertTrue(any("flat" in w for w in e.warnings))

        # validation contract on every building
        from btools.api.validate import validate_object

        for name in (
            "a_gable_bld",
            "b_flat_bld",
            "c_angle_bld",
            "d_bare_bld",
            "e_fallback_bld",
        ):
            obj = bpy.data.objects[name]
            report = validate_object(obj, include_geometry=False)
            self.assertTrue(report["ok"], (name, report["problems"]))

        self.assertIn("5/5", batch_summary(results))

    def test_nonflat_skipped_with_error(self):
        foot = self._footprint("tilted", 0, lift=1.0)
        me = foot.data
        me.vertices[0].co.z += 0.5
        me.update()
        results = generate_batch([foot])
        self.assertEqual(results[0].status, "cancelled")
        self.assertTrue(results[0].errors)

    def test_dry_run_creates_nothing(self):
        import bpy

        foot = self._footprint("dry", 0, {"roof:shape": "gabled"})
        results = generate_batch([foot], BatchOptions(dry_run=True))
        self.assertEqual(results[0].status, "skipped")
        self.assertNotIn("dry_bld", bpy.data.objects)

    @staticmethod
    def _window_positions(name):
        """Rounded (x, y) of every window-group vertex (stable across the
        window op's strip-count nondeterminism)."""
        import bpy

        obj = bpy.data.objects[name]
        me = obj.data
        names = [mt.name for mt in getattr(obj, "bt_materials", [])]
        attr = me.attributes.get(".bt_material_group_index")
        vals = [0] * len(me.polygons)
        attr.data.foreach_get("value", vals)
        return sorted(
            (round(me.vertices[i].co.x, 3), round(me.vertices[i].co.y, 3))
            for p, t in zip(me.polygons, vals)
            if names[t] == "window"
            for i in p.vertices
        )

    def test_seeded_window_pass_reproducible(self):
        import bpy

        def run():
            for o in list(bpy.data.objects):
                bpy.data.objects.remove(o)
            foot = self._footprint(
                "w", 0, {"roof:shape": "gabled", "building:levels": 3}
            )
            opts = BatchOptions(window_density=0.7, seed=42)
            res = generate_batch([foot], opts)[0]
            self.assertTrue(res.ok, res.errors[:1])
            # -- CONTRACT: same seed decides the same window placements
            #    (the window op's strip geometry itself carries known
            #    bmesh nondeterminism, like door frames)
            return [d for d in res.decisions if d[0].startswith("window/")]

        dec1 = run()
        dec2 = run()
        self.assertTrue(dec1, "no windows placed")
        self.assertEqual(dec1, dec2)

    def test_operator_registered(self):
        import bpy

        self.assertTrue(hasattr(bpy.ops.btools, "batch_generate"))


if __name__ == "__main__":
    unittest.main()

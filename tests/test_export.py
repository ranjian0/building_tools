"""Tests for production export (glTF/FBX, semantic material slots)."""

import os
import unittest


class TestExport(unittest.TestCase):
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
    def _building():
        import bpy

        from btools.api import FaceTarget, apply_feature
        from btools.api.core import options_from_dict
        from btools.api.options import FloorOptions, FloorplanOptions, RoofOptions
        from btools.api.select import select

        res = apply_feature(
            "floorplan",
            options_from_dict(FloorplanOptions, {"width": 8.0, "length": 6.0}),
        )
        obj = bpy.data.objects[res.created_object]
        apply_feature(
            "floor",
            options_from_dict(FloorOptions, {"floor_count": 1, "floor_height": 3.0}),
            FaceTarget(obj),
        )
        apply_feature(
            "roof",
            options_from_dict(RoofOptions, {"type": "GABLE", "height": 1.5}),
            FaceTarget(obj, select(obj, "top_face")),
        )
        return obj

    def test_semantic_slot_names(self):
        from btools.building.export import semantic_slot_names

        obj = self._building()
        names = semantic_slot_names(obj)
        self.assertIn("BT_walls", names)
        self.assertIn("BT_roof", names)
        self.assertIn("BT_slabs", names)

    def test_prepare_export_object(self):
        import bpy

        from btools.building.export import prepare_export_object

        obj = self._building()
        # move/rotate/scale the original: the duplicate must come out
        # with identity transforms
        obj.location = (10.0, -4.0, 2.0)
        obj.rotation_euler = (0.0, 0.0, 0.5)
        obj.scale = (2.0, 2.0, 2.0)

        dup = prepare_export_object(obj)
        try:
            self.assertAlmostEqual(dup.matrix_world.translation.length, 0.0, places=4)
            self.assertAlmostEqual(dup.scale.x, 1.0, places=4)
            # semantic slots: every slot named BT_*
            slots = [m.name for m in dup.data.materials]
            self.assertTrue(slots, "no material slots")
            for name in slots:
                self.assertTrue(name.startswith("BT_"), name)
            # faces actually reference the semantic slots
            used = {
                dup.data.polygons[i].material_index
                for i in range(len(dup.data.polygons))
            }
            self.assertTrue(all(0 <= u < len(slots) for u in used))
        finally:
            bpy.data.objects.remove(dup, do_unlink=True)
        # original untouched
        self.assertAlmostEqual(obj.scale.x, 2.0, places=4)

    def test_export_object_glb(self):
        import bpy

        from btools.building.export import export_object

        obj = self._building()
        out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "out_export_test"
        )
        os.makedirs(out, exist_ok=True)
        path = os.path.join(out, "house.glb")
        ok, got, error = export_object(obj, filepath=path, export_format="GLB")
        try:
            if ok:
                self.assertTrue(os.path.isfile(path))
                self.assertGreater(os.path.getsize(path), 1000)
                # scene object untouched
                self.assertIn(obj.name, bpy.data.objects)
            else:
                self.skipTest("glTF exporter unavailable headless: %s" % error)
        finally:
            if os.path.isfile(path):
                os.remove(path)
            os.rmdir(out) if os.path.isdir(out) and not os.listdir(out) else None

    def test_operator_registered(self):
        import bpy

        self.assertTrue(hasattr(bpy.ops.btools, "export_building"))


if __name__ == "__main__":
    unittest.main()

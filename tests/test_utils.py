import unittest

import bmesh
import bpy
from mathutils import Vector

import btools


class TestUtilsCommon(unittest.TestCase):

    def test_equal(self):
        # -- default eps(0.001)
        self.assertTrue(btools.utils.equal(0.005, 0.006))
        self.assertFalse(btools.utils.equal(0.005, 0.0061))

        # -- higher eps(0.0001)
        self.assertFalse(btools.utils.equal(0.005, 0.006, 0.0001))

    def test_clamp(self):
        self.assertEqual(btools.utils.clamp(2, 0.2, 1), 1)
        self.assertEqual(btools.utils.clamp(0.1, 0.2, 1), 0.2)

    def test_crashsafe(self):

        @btools.utils.crash_safe
        def run_failed():
            raise IndexError
            return {"FINISHED"}

        @btools.utils.crash_safe
        def run_passed():
            return {"FINISHED"}

        class DummyOpFail(bpy.types.Operator):
            bl_idname = "btools_test.dummy_op_fail"
            bl_label = "Dummy Test Fail"
            bl_options = {"REGISTER", "UNDO"}

            def execute(self, context):
                return run_failed()

        bpy.utils.register_class(DummyOpFail)
        with btools.utils.suppress_stdout_stderr():
            res = bpy.ops.btools_test.dummy_op_fail()
            self.assertEqual(res, {"CANCELLED"})
        bpy.utils.unregister_class(DummyOpFail)

        class DummyOpPass(bpy.types.Operator):
            bl_idname = "btools_test.dummy_op_pass"
            bl_label = "Dummy Test Pass"
            bl_options = {"REGISTER", "UNDO"}

            def execute(self, context):
                return run_passed()

        bpy.utils.register_class(DummyOpPass)
        res = bpy.ops.btools_test.dummy_op_pass()
        self.assertEqual(res, {"FINISHED"})
        bpy.utils.unregister_class(DummyOpPass)

    def test_restricted_sizeoffset(self):
        # XXX OFFSET
        # -- restrict sane
        self.assertEqual(
            btools.utils.restricted_offset([1, 1], [0.5, 0.5], [0, 0]), (0, 0))

        # -- restrict min
        self.assertEqual(
            btools.utils.restricted_offset([1, 1], [0.5, 0.5], [-1, -1]), (-0.25, -0.25))

        # -- restrict max
        self.assertEqual(
            btools.utils.restricted_offset([1, 1], [0.5, 0.5], [1, 1]), (0.25, 0.25))

        # XXX SIZE
        # -- restrict sane
        self.assertEqual(
            btools.utils.restricted_size([1, 1], [0, 0], [0, 0], [0.5, 0.5]), (0.5, 0.5))

        # -- restrict min
        self.assertEqual(
            btools.utils.restricted_size([1, 1], [0, 0], [1, 1], [0.5, 0.5]), (1, 1))

        # -- restrict with offset
        self.assertEqual(
            btools.utils.restricted_size([1, 1], [0.5, 0.5], [0.5, 0.5], [0.75, 0.75]), (0.5, 0.5))

    def test_local_to_global(self):
        X = Vector((1, 0, 0))
        Y = Vector((0, 1, 0))

        class Face:
            pass

        dummy = Face()
        dummy.normal = Vector()

        self.assertEqual(btools.utils.local_to_global(dummy, Vector()), Vector())

        dummy.normal = Y
        gb = btools.utils.local_to_global(dummy, X)
        self.assertEqual(gb.to_tuple(1), Vector((-1, 0, 0)).to_tuple(1))

        dummy.normal = X
        gb = btools.utils.local_to_global(dummy, Y)
        self.assertEqual(gb.to_tuple(1), Vector((0, 0, 1)).to_tuple(1))

    def test_local_xyz(self):
        class Face:
            pass

        dummy = Face()
        dummy.normal = Vector()

        self.assertEqual(btools.utils.local_xyz(dummy), (Vector(),)*3)

        dummy.normal = Vector((1, 0, 0))
        x, y, z = btools.utils.local_xyz(dummy)
        self.assertEqual(x.to_tuple(1), Vector((0, 1, 0)).to_tuple(1))
        self.assertEqual(y.to_tuple(1), Vector((0, 0, 1)).to_tuple(1))
        self.assertEqual(z.to_tuple(1), Vector((1, 0, 0)).to_tuple(1))

        dummy.normal = Vector((0, 1, 0))
        x, y, z = btools.utils.local_xyz(dummy)
        self.assertEqual(x.to_tuple(1), Vector((-1, 0, 0)).to_tuple(1))
        self.assertEqual(y.to_tuple(1), Vector((0, 0, 1)).to_tuple(1))
        self.assertEqual(z.to_tuple(1), Vector((0, 1, 0)).to_tuple(1))

        dummy.normal = Vector((0, 0, 1))
        x, y, z = btools.utils.local_xyz(dummy)
        self.assertEqual(x.to_tuple(1), Vector((0, 0, 1)).to_tuple(1))
        self.assertEqual(y.to_tuple(1), Vector((0, 0, 0)).to_tuple(1))
        self.assertEqual(z.to_tuple(1), Vector((0, 0, 1)).to_tuple(1))


class TestUtilsGeometry(unittest.TestCase):

    def setUp(self):
        self.bm = bmesh.new()

    def tearDown(self):
        self.bm.free()

    def clean_bmesh(self):
        [self.bm.verts.remove(v) for v in self.bm.verts]

    def test_cube(self):
        btools.utils.cube(self.bm)
        self.assertEquals(len(self.bm.faces), 6)
        self.assertEquals(len(self.bm.verts), 8)

    def test_plane(self):
        btools.utils.plane(self.bm)
        self.assertEquals(len(self.bm.faces), 1)
        self.assertEquals(len(self.bm.verts), 4)

    def test_circle(self):
        btools.utils.circle(self.bm)
        self.assertEquals(len(self.bm.faces), 1)
        self.assertEquals(len(self.bm.verts), 10)

        self.clean_bmesh()

        btools.utils.circle(self.bm, segs=12, cap_tris=True)
        self.assertEquals(len(self.bm.faces), 12)
        self.assertEquals(len(self.bm.verts), 13)

    def test_cone(self):
        btools.utils.cone(self.bm)
        self.assertEquals(len(self.bm.faces), 96)
        self.assertEquals(len(self.bm.verts), 66)

    def test_cylinder(self):
        btools.utils.cylinder(self.bm)
        self.assertEquals(len(self.bm.faces), 11)
        self.assertEquals(len(self.bm.verts), 20)

    def test_cube_without_faces(self):
        btools.utils.create_cube_without_faces(
            self.bm, Vector((1, 1, 1)))
        self.assertEquals(len(self.bm.faces), 6)
        self.assertEquals(len(self.bm.verts), 8)

        self.clean_bmesh()

        btools.utils.create_cube_without_faces(
            self.bm, Vector((1, 1, 1)), top=True, bottom=True)
        self.assertEquals(len(self.bm.faces), 4)
        self.assertEquals(len(self.bm.verts), 8)

        self.clean_bmesh()

        btools.utils.create_cube_without_faces(
            self.bm, Vector((1, 1, 1)), top=True, bottom=True,
            left=True, right=True, front=True, back=True)
        self.assertEquals(len(self.bm.faces), 0)
        self.assertEquals(len(self.bm.verts), 8)

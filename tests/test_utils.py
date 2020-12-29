import bmesh
import bpy
import btools
import math
import random
import unittest

from mathutils import Vector


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

    def test_minmax(self):
        self.assertEqual(btools.utils.minmax(range(10)), (0, 9))
        self.assertEqual(btools.utils.minmax([-1, 0]), (-1, 0))

        # -- test with keyfunction
        vecs = [Vector(tup) for tup in zip(range(10), range(10, 0, -1))]
        res = btools.utils.minmax(vecs, key=lambda v: v.y)
        self.assertEqual(res[0], Vector((9.0, 1.0)))
        self.assertEqual(res[1], Vector((0.0, 10.0)))

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
        self.assertEqual(gb.to_tuple(1), Vector((1, 0, 0)).to_tuple(1))

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
        self.assertEqual(x.to_tuple(1), Vector((0, -1, 0)).to_tuple(1))
        self.assertEqual(y.to_tuple(1), Vector((0, 0, 1)).to_tuple(1))
        self.assertEqual(z.to_tuple(1), Vector((1, 0, 0)).to_tuple(1))

        dummy.normal = Vector((0, 1, 0))
        x, y, z = btools.utils.local_xyz(dummy)
        self.assertEqual(x.to_tuple(1), Vector((1, 0, 0)).to_tuple(1))
        self.assertEqual(y.to_tuple(1), Vector((0, 0, 1)).to_tuple(1))
        self.assertEqual(z.to_tuple(1), Vector((0, 1, 0)).to_tuple(1))

        dummy.normal = Vector((0, 0, 1))
        x, y, z = btools.utils.local_xyz(dummy)
        self.assertEqual(x.to_tuple(1), Vector((0, 1, 0)).to_tuple(1))
        self.assertEqual(y.to_tuple(1), Vector((1, 0, 0)).to_tuple(1))
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


class TestUtilsMesh(unittest.TestCase):
    def setUp(self):
        self.bm = bmesh.new()

    def tearDown(self):
        self.bm.free()

    def clean_bmesh(self):
        [self.bm.verts.remove(v) for v in self.bm.verts]

    def test_create_mesh(self):
        me = btools.utils.create_mesh("test_mesh")
        self.assertIsNotNone(me)
        self.assertEqual(me.name, "test_mesh")

    def test_validate(self):
        btools.utils.cube(self.bm) 
        faces = btools.utils.validate(self.bm.faces)
        self.assertEqual(len(faces), 6)

        bmesh.ops.delete(self.bm, geom=[faces[0]], context="FACES_ONLY")

        self.assertEqual(len(faces), 6)
        self.assertEqual(len(btools.utils.validate(faces)), 5)

    def test_filtergeom(self):
        btools.utils.plane(self.bm)
        fg = btools.utils.filter_geom
        geom = list(self.bm.verts) + list(self.bm.edges) + list(self.bm.faces)
        self.assertEqual(len(fg(geom, bmesh.types.BMVert)), 4)
        self.assertEqual(len(fg(geom, bmesh.types.BMEdge)), 4)
        self.assertEqual(len(fg(geom, bmesh.types.BMFace)), 1)

    def test_edgetangent(self):
        btools.utils.plane(self.bm)
        et = btools.utils.edge_tangent
        fm = list(self.bm.faces).pop().calc_center_median()

        for edge in self.bm.edges:
            em = btools.utils.calc_edge_median(edge)
            self.assertEqual(
                et(edge).to_tuple(1),
                (fm-em).normalized().to_tuple(1)
            )

    def test_edgevector(self):
        btools.utils.plane(self.bm)
        ev = btools.utils.edge_vector
        self.assertEqual(
            sum([ev(e) for e in self.bm.edges], Vector()), Vector()
        )

    def test_edgeslope(self):
        btools.utils.plane(self.bm)
        es = btools.utils.edge_slope
        self.assertEqual(sum(es(e) for e in self.bm.edges), 0.0)

        self.clean_bmesh()
        btools.utils.cube(self.bm)
        slopes = [es(e) for e in self.bm.edges]
        self.assertEqual(len([s for s in slopes if s == 0]), 8)
        self.assertEqual(len([s for s in slopes if s == float('inf')]), 4)

        angles = [btools.utils.edge_angle(e) for e in self.bm.edges]
        self.assertEqual(len([a for a in angles if a == 0]), 8)
        self.assertEqual(len([a for a in angles if round(a, 4) == round(math.pi / 2, 4)]), 4)

        self.assertEqual(len([e for e in self.bm.edges if btools.utils.edge_is_vertical(e)]), 4)
        self.assertEqual(len([e for e in self.bm.edges if btools.utils.edge_is_horizontal(e)]), 8)
        self.assertEqual(len([e for e in self.bm.edges if btools.utils.edge_is_sloped(e)]), 0)

    def test_vec_equalopposite(self):
        LEFT = Vector((-1, 0, 0))
        RIGHT = Vector((1, 0, 0))

        self.assertTrue(btools.utils.vec_equal(RIGHT, RIGHT))
        self.assertTrue(btools.utils.vec_equal(RIGHT, RIGHT*1.0001))
        self.assertTrue(btools.utils.vec_equal(RIGHT, RIGHT*0.0009))

        self.assertTrue(btools.utils.vec_opposite(RIGHT, LEFT))

    def test_filteredges(self):
        # -- 2D
        btools.utils.plane(self.bm)
        self.assertEqual(len(btools.utils.filter_vertical_edges(self.bm.edges)), 2)
        self.assertEqual(len(btools.utils.filter_horizontal_edges(self.bm.edges)), 2)

        self.clean_bmesh()
        # -- 3D
        btools.utils.cube(self.bm)
        self.assertEqual(len(btools.utils.filter_vertical_edges(self.bm.edges)), 4)
        self.assertEqual(len(btools.utils.filter_horizontal_edges(self.bm.edges)), 8)

        # -- 3D Sloped
        top_face = [f for f in self.bm.faces if f.normal.z > 0].pop()
        bmesh.ops.scale(self.bm, verts=top_face.verts, vec=(0.2, 1, 1))
        self.assertEqual(len(btools.utils.filter_vertical_edges(self.bm.edges)), 4)

        # -- parallel
        self.assertEqual(len(btools.utils.filter_parallel_edges(self.bm.edges, Vector((1, 0, 0)))), 4)

    def test_rectangular_ngon(self):
        btools.utils.plane(self.bm)

        self.assertTrue(btools.utils.valid_ngon(list(self.bm.faces).pop()))
        self.assertTrue(btools.utils.is_rectangle(list(self.bm.faces).pop()))

        hedges = btools.utils.filter_horizontal_edges(self.bm.edges)
        bmesh.ops.subdivide_edges(self.bm, edges=[hedges[0]], cuts=2)
        bmesh.ops.subdivide_edges(self.bm, edges=[hedges[1]], cuts=2)

        self.assertFalse(btools.utils.valid_ngon(list(self.bm.faces).pop()))

        v = random.choice([v for v in self.bm.verts])
        v.co += Vector((random.random() * 19, random.random() * 5, 0))
        self.assertFalse(btools.utils.is_rectangle(list(self.bm.faces).pop()))

    def test_median_dimensions(self):
        btools.utils.plane(self.bm)

        f = list(self.bm.faces).pop()
        self.assertEqual(btools.utils.calc_face_dimensions(f), (4, 4))
        self.assertEqual(btools.utils.calc_verts_median(f.verts), Vector())

        self.clean_bmesh()
        btools.utils.cube(self.bm) 
        self.assertEqual(btools.utils.calc_faces_median(self.bm.faces), Vector())
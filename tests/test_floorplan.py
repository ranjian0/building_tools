import bpy
import btools
import unittest

floorplan = btools.core.floorplan
builder = floorplan.floorplan.Floorplan


class TestFloorplan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        bpy.utils.register_class(btools.core.floorplan.FloorplanProperty)
        bpy.types.Scene.test_prop = bpy.props.PointerProperty(type=btools.core.floorplan.FloorplanProperty)

    @classmethod
    def tearDownClass(cls):
        del bpy.types.Scene.test_prop
        bpy.utils.unregister_class(btools.core.floorplan.FloorplanProperty)

    def setUp(self):
        self.clear_objects()
        self.defaults = btools.utils.kwargs_from_props(bpy.context.scene.test_prop)

    def tearDown(self):
        # -- restore test_prop to previous state
        for key, val in self.defaults.items():
            setattr(bpy.context.scene.test_prop, key, val)

    def clear_objects(self):
        [bpy.data.objects.remove(o) for o in bpy.data.objects]

    def test_flooplan_op(self):
        res = bpy.ops.btools.add_floorplan()
        self.assertEqual(res, {"FINISHED"})

        obj = bpy.context.object
        self.assertIsNotNone(obj)

    def test_rectangular(self):
        context = bpy.context
        prop = context.scene.test_prop

        res = builder.build(context, prop)
        self.assertIsNotNone(res)

        verts = context.object.data.vertices
        self.assertEquals(len(verts), 4)

        # -- check default size
        srt = sorted([v.co for v in verts], key=lambda co: co.xy.to_tuple(2))
        self.assertEqual((srt[-1] - srt[0]).xy.to_tuple(1), (4.0, 4.0))

        self.clear_objects()

        prop.width = 10
        prop.length = 10
        res = builder.build(context, prop)
        self.assertIsNotNone(res)

        # -- check new size
        verts = context.object.data.vertices
        srt = sorted([v.co for v in verts], key=lambda co: co.xy.to_tuple(2))
        self.assertEqual((srt[-1] - srt[0]).xy.to_tuple(1), (10.0, 10.0))

    def test_circular(self):
        context = bpy.context
        prop = context.scene.test_prop

        prop.type = "CIRCULAR"
        res = builder.build(context, prop)
        self.assertIsNotNone(res)

        faces = context.object.data.polygons
        self.assertEquals(len(faces), 1) # cap_tris False

        # -- check default size
        verts = context.object.data.vertices
        srt_x = sorted([v.co for v in verts], key=lambda co: co.x)
        self.assertEqual((srt_x[-1] - srt_x[0]).x, prop.radius * 2)

        srt_y = sorted([v.co for v in verts], key=lambda co: co.y)
        self.assertEqual((srt_y[-1] - srt_y[0]).y, prop.radius * 2)

        self.clear_objects()

        prop.cap_tris = True
        res = builder.build(context, prop)
        self.assertIsNotNone(res)

        faces = context.object.data.polygons
        self.assertEquals(len(faces), prop.segments) # cap_tris False

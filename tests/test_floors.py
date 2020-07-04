import bpy
import btools
import unittest

floor = btools.core.floor
builder = floor.floor.Floor


class TestFloor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        bpy.utils.register_class(floor.FloorProperty)
        bpy.types.Scene.floor_prop = bpy.props.PointerProperty(type=floor.FloorProperty)

    @classmethod
    def tearDownClass(cls):
        del bpy.types.Scene.floor_prop
        bpy.utils.unregister_class(floor.FloorProperty)

    def setUp(self):
        self.clear_objects()
        self.defaults = btools.utils.kwargs_from_props(bpy.context.scene.floor_prop)

    def tearDown(self):
        # -- restore test_prop to previous state
        for key, val in self.defaults.items():
            setattr(bpy.context.scene.floor_prop, key, val)

    def clear_objects(self):
        [bpy.data.objects.remove(o) for o in bpy.data.objects]

    def test_floor(self):
        self.assertTrue(True)
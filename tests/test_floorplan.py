import bpy
import unittest


class TestProps:
    pass


class TestFloorplan(unittest.TestCase):

    def test_flooplan_op(self):
        res = bpy.ops.btools.add_floorplan()
        self.assertEqual(res, {"FINISHED"})

        obj = bpy.context.object
        self.assertIsNotNone(obj)

        self.assertEquals(len(obj.data.vertices), 4)

import bpy
import btools
import random
import unittest

floor = btools.building.floor
floor_builder = floor.floor.Floor

floorplan = btools.building.floorplan
floorplan_builder = floorplan.floorplan.Floorplan


class TestFloor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bpy.utils.register_class(floorplan.FloorplanProperty)
        bpy.types.Scene.floorplan_prop = bpy.props.PointerProperty(type=floorplan.FloorplanProperty)

        bpy.utils.register_class(floor.FloorProperty)
        bpy.types.Scene.floor_prop = bpy.props.PointerProperty(type=floor.FloorProperty)

    @classmethod
    def tearDownClass(cls):
        del bpy.types.Scene.floor_prop
        bpy.utils.unregister_class(floor.FloorProperty)

        del bpy.types.Scene.floorplan_prop
        bpy.utils.unregister_class(floorplan.FloorplanProperty)

    def setUp(self):
        self.clear_objects()
        self.defaults = btools.utils.dict_from_prop(bpy.context.scene.floor_prop)

    def tearDown(self):
        # -- restore test_prop to previous state
        for key, val in self.defaults.items():
            setattr(bpy.context.scene.floor_prop, key, val)

    def clear_objects(self):
        [bpy.data.objects.remove(o) for o in bpy.data.objects]

    def iter_floorplans(self):
        """ Build some floorplans for testing floor tools"""
        context = bpy.context
        prop = context.scene.floorplan_prop

        # Build regular shapes
        for fp_type in ["RECTANGULAR", "CIRCULAR", "COMPOSITE"]:
            prop.type = fp_type
            res = floorplan_builder.build(context, prop)

            # switch to edit mode
            bpy.ops.object.editmode_toggle()

            yield res

            # switch back to object mode
            bpy.ops.object.editmode_toggle()

            # -- clear
            self.clear_objects()

        # Build random shapes
        prop.type = "RANDOM"
        for s in range(25):
            prop.seed = random.randrange(0, 10000)
            res = floorplan_builder.build(context, prop)

            # switch to edit mode
            bpy.ops.object.editmode_toggle()

            yield res

            # switch back to object mode
            bpy.ops.object.editmode_toggle()

            # -- clear
            self.clear_objects()

    def test_floors_multi(self):
        context = bpy.context
        prop = context.scene.floor_prop
        for _ in self.iter_floorplans():

            with btools.utils.bmesh_from_active_object(context) as bm:
                # Number of faces in the floorplan
                self.assertTrue(1 <= len(bm.faces) <= 10)
                floorplan_edges_count = len([e for e in bm.edges if e.is_boundary])

                # build floor
                floor_res = floor_builder.build(context, prop)
                self.assertEqual(floor_res, {"FINISHED"})
                self.assertEqual(len(bm.faces), (floorplan_edges_count * 4) + 1)

    def test_floors_multi_visual(self):
        # --run some floor tests and save the blend file for visual confirmation
        pass

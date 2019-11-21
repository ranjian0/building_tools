import bpy
import random
import operator as op
from ..core.floorplan import FloorplanProperty
from ..core.floorplan.floorplan import Floorplan


class BTOOLS_OT_test_floorplan(bpy.types.Operator):
    """ Test creation of building floorplans """

    bl_idname = "btools.test_floorplan"
    bl_label = "Test Floorplan"

    collection_name = "test_floorplans"
    props: bpy.props.PointerProperty(type=FloorplanProperty)

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        # -- remove objects if any
        test_col = bpy.context.scene.collection.children.get(self.collection_name)
        if len(test_col.objects):
            list(map(bpy.data.objects.remove, test_col.objects))

        # -- create various types of floorplans
        random_floorplans(self, context, test_col)
        return {"FINISHED"}


def random_floorplans(self, context, collection):
    objects = []
    fp_types = list(map(op.itemgetter(0), self.props.fp_types))
    positions = [(0, 0, 0), (-20, 20, 0), (20, 20, 0), (20, -20, 0), (-20, -20, 0)]
    for _type, pos in zip(fp_types, positions):
        # -- random attributes
        self.props.type = _type
        self.props.tl1 = random.randrange(2, 10)
        self.props.tl2 = random.randrange(2, 10)
        self.props.tl3 = random.randrange(2, 10)
        self.props.tl4 = random.randrange(2, 10)
        self.props.tw1 = random.randrange(2, 10)
        self.props.tw2 = random.randrange(2, 10)
        self.props.tw3 = random.randrange(2, 10)
        self.props.tw4 = random.randrange(2, 10)
        self.props.width = random.randrange(3, 10)
        self.props.length = random.randrange(2, 10)
        self.props.radius = random.randrange(3, 10)
        self.props.seed = random.randrange(100, 500)
        self.props.segments = random.randrange(16, 32)

        # -- create object
        obj = Floorplan.build(context, self.props)
        obj.name = 'floorplan_test_' + _type.lower()
        obj.location = pos

        # -- move to proper collection
        bpy.context.scene.collection.objects.unlink(obj)
        collection.objects.link(obj)

        # -- exclude all other collections apart from test_col from view layer
        for layer_col in bpy.context.view_layer.layer_collection.children:
            layer_col.exclude = True
            if layer_col.name == collection.name:
                layer_col.exclude = False

        obj.select_set(False)
        objects.append(obj)
    return objects

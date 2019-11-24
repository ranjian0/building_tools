import bpy
import random
from .test_floorplan import random_floorplans

from ..core.floor import FloorProperty
from ..core.floorplan import FloorplanProperty
from ..utils import bm_from_obj, bm_to_obj
from ..core.floor.floor_types import create_floors


class BTOOLS_OT_test_floors(bpy.types.Operator):
    """ Test creation of building floorplans """

    bl_idname = "btools.test_floors"
    bl_label = "Test Floor"

    collection_name = "test_floors"
    fprops: bpy.props.PointerProperty(type=FloorProperty)
    props: bpy.props.PointerProperty(type=FloorplanProperty)

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        # -- remove objects if any
        test_col = bpy.context.scene.collection.children.get(self.collection_name)
        if len(test_col.objects):
            list(map(bpy.data.meshes.remove, [ob.data for ob in test_col.objects]))
            list(map(bpy.data.objects.remove, test_col.objects))

        random_floors(self, context, test_col)
        return {"FINISHED"}


def random_floors(self, context, collection):
    # -- create various types of floors
    floorplans = random_floorplans(self, context, collection)

    # -- create random floors
    for fp in floorplans:
        self.fprops.floor_count = random.randrange(1, 15)
        bm = bm_from_obj(fp)
        edges = [e for e in bm.edges if e.is_boundary]
        create_floors(bm, edges, self.fprops)
        bm_to_obj(bm, fp)

import bpy
import operator as op
import itertools as it
from ..core.rails import RailProperty
from ..core.rails.rails_types import create_railing_from_selection
from ..utils import bm_to_obj, bm_from_obj, create_object, create_mesh


RAIL_TYPES_CYCLE = None
CURRENT_RAIL_TYPE = None


class BTOOLS_OT_test_railing(bpy.types.Operator):
    """ Test creation of building railing """

    bl_idname = "btools.test_railing"
    bl_label = "Test Railing"

    collection_name = "test_railing"
    props: bpy.props.PointerProperty(type=RailProperty)

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        # -- cycle through different rail tyoes
        global RAIL_TYPES_CYCLE, CURRENT_RAIL_TYPE
        if not RAIL_TYPES_CYCLE:
            RAIL_TYPES_CYCLE = it.cycle(map(op.itemgetter(0), self.props.fill_types))
        CURRENT_RAIL_TYPE = next(RAIL_TYPES_CYCLE)

        # -- remove object copies if any
        test_col = bpy.context.scene.collection.children.get(self.collection_name)
        for obj in test_col.objects:
            if 'copy' in obj.name:
                bpy.data.meshes.remove(obj.data)
                # bpy.data.objects.remove(obj)

        random_railing(self, context, test_col)
        return {"FINISHED"}


def random_railing(self, context, collection):
    # -- duplicate data from all objects in the collection
    for obj in collection.objects:
        # XXX Just in case
        if 'copy' in obj.name:
            continue

        bm = bm_from_obj(obj).copy()
        obj_copy = create_object(obj.name+'_copy', create_mesh(obj.data.name + '_copy'))
        obj_copy.location = obj.location

        self.props.fill = CURRENT_RAIL_TYPE
        create_railing_from_selection(bm, self.props)
        bm_to_obj(bm, obj_copy)
        collection.objects.link(obj_copy)

    # -- exclude all other collections apart from test_col from view layer
    for layer_col in bpy.context.view_layer.layer_collection.children:
        layer_col.exclude = not (layer_col.name == collection.name)

    # -- hide objects that are not copies
    for obj in collection.objects:
        if 'copy' not in obj.name:
            obj.hide_viewport = True

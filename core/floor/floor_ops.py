import bpy
from .floor import Floor
from .floor_props import FloorProperty
from ...utils import FaceMap


class BTOOLS_OT_add_floors(bpy.types.Operator):

    bl_idname = "btools.add_floors"
    bl_label = "Add Floors"
    bl_options = {"REGISTER", "UNDO"}

    props: bpy.props.PointerProperty(type=FloorProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        ob = context.object
        wall_map = ob.user_facemaps.add()
        wall_map.name = FaceMap.WALLS.name.lower()

        slab_map = ob.user_facemaps.add()
        slab_map.name = FaceMap.SLABS.name.lower()
        return Floor.build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)

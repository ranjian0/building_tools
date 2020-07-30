import bpy

from .stairs import Stairs
from .stairs_props import StairsProperty
from ...utils import get_selected_face_dimensions


class BTOOLS_OT_add_stairs(bpy.types.Operator):
    """Create stairs from selected faces"""

    bl_idname = "btools.add_stairs"
    bl_label = "Add Stairs"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=StairsProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        self.props.init(get_selected_face_dimensions(context))
        return Stairs.build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)

import bpy

from .multigroup import Multigroup
from .multigroup_props import MultigroupProperty
from ...utils import get_selected_face_dimensions


class BTOOLS_OT_add_multigroup(bpy.types.Operator):
    """Create multiple door/window group from selected faces"""

    bl_idname = "btools.add_multigroup"
    bl_label = "Add Multigroup"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=MultigroupProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        self.props.init(get_selected_face_dimensions(context))
        return Multigroup.build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)

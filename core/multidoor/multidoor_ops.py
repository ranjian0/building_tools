import bpy
from .multidoor import Multidoor
from .multidoor_props import MultidoorProperty
from ...utils import get_selected_face_dimensions


class BTOOLS_OT_add_multidoor(bpy.types.Operator):
    """Create a multidoor from selected faces"""

    bl_idname = "btools.add_multidoor"
    bl_label = "Add Multidoor"
    bl_options = {"REGISTER", "UNDO"}

    props: bpy.props.PointerProperty(type=MultidoorProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        self.props.init(get_selected_face_dimensions(context))
        return Multidoor.build(self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)

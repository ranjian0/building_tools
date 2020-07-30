import bpy

from .roof import Roof
from .roof_props import RoofProperty


class BTOOLS_OT_add_roof(bpy.types.Operator):
    """Create roof from selected upward facing faces"""

    bl_idname = "btools.add_roof"
    bl_label = "Add Roof"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=RoofProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        return Roof.build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)

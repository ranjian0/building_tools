import bpy

from .fill import Fill
from .fill_props import FillProperty


class BTOOLS_OT_add_fill(bpy.types.Operator):
    """Add fill to selected faces"""

    bl_idname = "btools.add_fill"
    bl_label = "Add Fill"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=FillProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        return Fill.build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)

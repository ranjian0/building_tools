import bpy
from .window import Window
from .window_props import WindowProperty


class BTOOLS_OT_add_window(bpy.types.Operator):

    bl_idname = "btools.add_window"
    bl_label = "Add Window"
    bl_options = {"REGISTER", "UNDO"}

    props: bpy.props.PointerProperty(type=WindowProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        return Window.build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)

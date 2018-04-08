import bpy
from .window import Window
from .window_props import WindowProperty

class WindowOperator(bpy.types.Operator):
    """ Creates windows on selected mesh faces """
    bl_idname = "cynthia.add_window"
    bl_label = "Add Window"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=WindowProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        Window.build(context, self.props)
        return {'FINISHED'}

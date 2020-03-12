import bpy, bmesh
from .window import Window
from .window_props import WindowProperty
from ...utils import get_width_and_height


class BTOOLS_OT_add_window(bpy.types.Operator):
    """Create window from selected faces"""

    bl_idname = "btools.add_window"
    bl_label = "Add Window"
    bl_options = {"REGISTER", "UNDO"}

    props: bpy.props.PointerProperty(type=WindowProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        bm = bmesh.from_edit_mesh(context.edit_object.data)
        wall = [f for f in bm.faces if f.select][0]
        self.wall_dimensions = get_width_and_height(wall)
        self.props.wall_dimensions = self.wall_dimensions

        return Window.build(context, self.props)

    def draw(self, context):
        self.props.wall_dimensions = self.wall_dimensions

        self.props.draw(context, self.layout)

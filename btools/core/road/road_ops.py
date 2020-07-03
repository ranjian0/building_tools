import bpy
from .road import Road
from .road_props import RoadProperty


class BTOOLS_OT_add_road(bpy.types.Operator):
    """Create road from selected curve"""

    bl_idname = "btools.add_road"
    bl_label = "Add Road"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=RoadProperty)

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        Road.build(context, self.props)
        return {"FINISHED"}

    def draw(self, context):
        self.props.draw(context, self.layout)

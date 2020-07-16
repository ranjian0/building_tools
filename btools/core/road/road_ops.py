import bpy
from .road import Road
from .road_props import RoadProperty, RoadExtrudeProperty


class BTOOLS_OT_add_road(bpy.types.Operator):
    """Create road vertex outline
    """

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

    def cancel(self, context):
        print("TEST")


class BTOOLS_OT_extrude_road(bpy.types.Operator):
    """Extrude road vertex outline
    """

    bl_idname = "btools.extrude_road"
    bl_label = "Extrude Road"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=RoadExtrudeProperty)

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        Road.extrude(context, self.props)
        return {"FINISHED"}

    def draw(self, context):
        self.props.draw(context, self.layout)
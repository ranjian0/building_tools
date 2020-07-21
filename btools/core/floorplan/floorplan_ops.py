import bpy

from .floorplan import Floorplan
from .floorplan_props import FloorplanProperty


class BTOOLS_OT_add_floorplan(bpy.types.Operator):
    """Create a starting building floorplan"""

    bl_idname = "btools.add_floorplan"
    bl_label = "Create Floorplan"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=FloorplanProperty)

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        Floorplan.build(context, self.props)
        return {"FINISHED"}

    def draw(self, context):
        self.props.draw(context, self.layout)

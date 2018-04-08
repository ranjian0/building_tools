import bpy
from .floorplan import Floorplan
from .floorplan_props import FloorplanProperty

class FloorplanOperator(bpy.types.Operator):
    """ Create a floorplan object """
    bl_idname = "cynthia.add_floorplan"
    bl_label = "Create Floorplan"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=FloorplanProperty)

    def execute(self, context):
        Floorplan.build(context, self.props)
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        self.props.draw(context, layout)


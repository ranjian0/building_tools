import bpy
from .stairs import Stairs
from .stairs_props import StairsProperty

class StairsOperator(bpy.types.Operator):
    """ Creates stairs on selected mesh faces """
    bl_idname = "cynthia.add_stairs"
    bl_label = "Add Stairs"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=StairsProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        self.props.set_defaults()
        return Stairs.build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)



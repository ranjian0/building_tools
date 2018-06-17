import bpy
from .rails import Rails
from .rails_props import RailProperty


class RailOperator(bpy.types.Operator):
    """ Creates rails on selected mesh edges """
    bl_idname = "cynthia.add_railing"
    bl_label = "Add Railing"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=RailProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        return Rails.build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)


import bpy
from .balcony import Balcony
from .balcony_props import BalconyProperty


class BalconyOperator(bpy.types.Operator):
    """ Creates balcony on selected mesh faces """
    bl_idname = "cynthia.add_balcony"
    bl_label = "Add Balcony"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=BalconyProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        return Balcony.build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)


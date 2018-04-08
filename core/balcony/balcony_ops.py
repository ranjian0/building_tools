import bpy
from .balcony import Balcony
from .balcony_props import BalconyProperty


class BalconyOperator(bpy.types.Operator):
    """ Creates doors on selected mesh faces """
    bl_idname = "cynthia.add_balcony"
    bl_label = "Add Balcony"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=BalconyProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        Balcony.build(context, self.props)
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        self.props.draw(context, layout)


import bpy
from .door import Door
from .door_props import DoorProperty


class DoorOperator(bpy.types.Operator):
    """ Creates doors on selected mesh faces """
    bl_idname = "cynthia.add_door"
    bl_label = "Add Door"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=DoorProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        self.props.set_defaults()
        Door.build(self.props)
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        self.props.draw(context, layout)


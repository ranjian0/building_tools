import bpy
from .door import Door


class DoorOperator(bpy.types.Operator):
    """ Creates doors on selected mesh faces """
    bl_idname = "cynthia.add_door"
    bl_label = "Add Door"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        Door.build(context)
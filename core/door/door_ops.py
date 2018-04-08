import bpy
from .door import Door
from .door_props import DoorProperty


class DoorOperator(bpy.types.Operator):
    """ Creates doors on selected mesh faces """
    bl_idname = "cynthia.add_door"
    bl_label = "Add Door"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=DoorProperty)

    def execute(self, context):
        Door.build(context, props)
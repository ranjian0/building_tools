import bpy

from .door_ops import BTOOLS_OT_add_door
from .door_props import DoorProperty

classes = (DoorProperty, BTOOLS_OT_add_door)


def register_door():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_door():
    for cls in classes:
        bpy.utils.unregister_class(cls)

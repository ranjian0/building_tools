import bpy

from .door_ops import BTOOLS_OT_add_door
from .door_props import DoorProperty

classes = (DoorProperty, BTOOLS_OT_add_door)

register_door, unregister_door = bpy.utils.register_classes_factory(classes)

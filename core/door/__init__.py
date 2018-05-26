import bpy

from .door import Door
from .door_ops import DoorOperator
from .door_props import DoorProperty

classes = (
    DoorProperty, DoorOperator
)

def register_door():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_door():
    for cls in classes:
        bpy.utils.unregister_class(cls)

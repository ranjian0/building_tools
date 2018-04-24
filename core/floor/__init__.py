import bpy

from .floor import Floor
from .floor_ops import FloorOperator
from .floor_props import FloorProperty

classes = (
    FloorProperty, FloorOperator
)

def register_floor():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_floor():
    for cls in classes:
        bpy.utils.unregister_class(cls)
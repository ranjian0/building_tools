import bpy

from .floor_ops import BTOOLS_OT_add_floors
from .floor_props import FloorProperty

classes = (FloorProperty, BTOOLS_OT_add_floors)


def register_floor():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_floor():
    for cls in classes:
        bpy.utils.unregister_class(cls)

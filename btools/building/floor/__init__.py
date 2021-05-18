import bpy

from .floor_ops import BTOOLS_OT_add_floors
from .floor_props import FloorProperty

classes = (FloorProperty, BTOOLS_OT_add_floors)

register_floor, unregister_floor = bpy.utils.register_classes_factory(classes)

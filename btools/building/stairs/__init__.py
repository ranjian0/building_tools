import bpy

from .stairs_ops import BTOOLS_OT_add_stairs
from .stairs_props import StairsProperty

classes = (StairsProperty, BTOOLS_OT_add_stairs)

register_stairs, unregister_stairs = bpy.utils.register_classes_factory(classes)

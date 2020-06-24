import bpy

from .stairs import Stairs
from .stairs_ops import BTOOLS_OT_add_stairs
from .stairs_props import StairsProperty

classes = (StairsProperty, BTOOLS_OT_add_stairs)


def register_stairs():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_stairs():
    for cls in classes:
        bpy.utils.unregister_class(cls)

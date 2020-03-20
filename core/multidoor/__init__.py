import bpy

from .multidoor_ops import BTOOLS_OT_add_multidoor
from .multidoor_props import MultidoorProperty

classes = (MultidoorProperty, BTOOLS_OT_add_multidoor)


def register_multidoor():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_multidoor():
    for cls in classes:
        bpy.utils.unregister_class(cls)

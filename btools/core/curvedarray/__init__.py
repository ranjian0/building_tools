import bpy

from .curved_array_ops import BTOOLS_OT_add_curved_array, BTOOLS_OT_finalize_curved_array

classes = (BTOOLS_OT_add_curved_array, BTOOLS_OT_finalize_curved_array)


def register_curved_array():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_curved_array():
    for cls in classes:
        bpy.utils.unregister_class(cls)
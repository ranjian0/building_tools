import bpy

from .window_ops import BTOOLS_OT_add_window
from .window_props import WindowProperty

classes = (WindowProperty, BTOOLS_OT_add_window)


def register_window():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_window():
    for cls in classes:
        bpy.utils.unregister_class(cls)

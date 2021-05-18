import bpy

from .window_ops import BTOOLS_OT_add_window
from .window_props import WindowProperty

classes = (WindowProperty, BTOOLS_OT_add_window)

register_window, unregister_window = bpy.utils.register_classes_factory(classes)

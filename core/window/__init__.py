import bpy

from .window import Window
from .window_ops import WindowOperator
from .window_props import WindowProperty

classes = (
    WindowProperty, WindowOperator
)

def register_window():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_window():
    for cls in classes:
        bpy.utils.unregister_class(cls)

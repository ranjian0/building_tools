import bpy

from .fill_props import FillBars, FillPanel, FillLouver, FillGlassPanes, FillProperty
from .fill_ops import BTOOLS_OT_add_fill
from .fill_types import fill_face

classes = (FillBars, FillPanel, FillLouver, FillGlassPanes, FillProperty, BTOOLS_OT_add_fill)


def register_fill():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_fill():
    for cls in classes:
        bpy.utils.unregister_class(cls)

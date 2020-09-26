import bpy

from .fill_props import FillBars, FillPanel, FillLouver, FillGlassPanes
from .fill_types import fill_face

classes = (FillBars, FillPanel, FillLouver, FillGlassPanes)


def register_fill():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_fill():
    for cls in classes:
        bpy.utils.unregister_class(cls)

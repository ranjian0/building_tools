import bpy

from .roof import Roof
from .roof_ops import BTOOLS_OT_add_roof
from .roof_props import RoofProperty

classes = (RoofProperty, BTOOLS_OT_add_roof)


def register_roof():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_roof():
    for cls in classes:
        bpy.utils.unregister_class(cls)

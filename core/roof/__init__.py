import bpy

from .roof import Roof
from .roof_ops import RoofOperator
from .roof_props import RoofProperty

classes = (
    RoofProperty, RoofOperator
)

def register_roof():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_roof():
    for cls in classes:
        bpy.utils.unregister_class(cls)

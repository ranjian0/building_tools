import bpy

from .roof_ops import BTOOLS_OT_add_roof
from .roof_props import RoofProperty

classes = (RoofProperty, BTOOLS_OT_add_roof)

register_roof, unregister_roof = bpy.utils.register_classes_factory(classes)

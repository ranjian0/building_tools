import bpy

from .interior_ops import BTOOLS_OT_add_partitions
from .interior_props import InteriorProperty

classes = (InteriorProperty, BTOOLS_OT_add_partitions)

register_interior, unregister_interior = bpy.utils.register_classes_factory(classes)

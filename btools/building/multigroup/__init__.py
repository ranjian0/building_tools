import bpy

from .multigroup_ops import BTOOLS_OT_add_multigroup
from .multigroup_props import MultigroupProperty

classes = (MultigroupProperty, BTOOLS_OT_add_multigroup)

register_multigroup, unregister_multigroup = bpy.utils.register_classes_factory(classes)

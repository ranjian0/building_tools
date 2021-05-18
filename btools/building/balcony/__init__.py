import bpy

from .balcony_ops import BTOOLS_OT_add_balcony
from .balcony_props import BalconyProperty

classes = (BalconyProperty, BTOOLS_OT_add_balcony)

register_balcony, unregister_balcony = bpy.utils.register_classes_factory(classes)

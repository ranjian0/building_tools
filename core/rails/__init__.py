import bpy

from .rails import Rails
from .rails_ops import BTOOLS_OT_add_railing
from .rails_props import RailProperty
from .rails_types import CreateRailing

classes = (RailProperty, BTOOLS_OT_add_railing)


def register_rail():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_rail():
    for cls in classes:
        bpy.utils.unregister_class(cls)

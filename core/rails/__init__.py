import bpy

from .rails import Rails
from .rails_ops import RailOperator
from .rails_props import RailProperty
from .rails_types import MakeRailing

classes = (
    RailProperty, RailOperator
)

def register_rail():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_rail():
    for cls in classes:
        bpy.utils.unregister_class(cls)

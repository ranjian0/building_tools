import bpy

from .railing_props import (
    PostFillProperty,
    RailFillProperty,
    WallFillProperty,
    RailProperty,
)

classes = (
    PostFillProperty,
    RailFillProperty,
    WallFillProperty,
    RailProperty,
)

register_railing, unregister_railing = bpy.utils.register_classes_factory(classes)

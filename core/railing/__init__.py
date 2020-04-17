import bpy

from .railing_props import PostFillProperty, RailFillProperty, WallFillProperty, RailProperty

classes = (
    PostFillProperty,
    RailFillProperty,
    WallFillProperty,
    RailProperty,
)


def register_railing():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_railing():
    for cls in classes:
        bpy.utils.unregister_class(cls)

import bpy

from .road import Road
from .road_ops import BTOOLS_OT_add_road, BTOOLS_OT_finalize_road
from .road_props import RoadProperty

classes = (RoadProperty, BTOOLS_OT_add_road, BTOOLS_OT_finalize_road)


def register_road():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_road():
    for cls in classes:
        bpy.utils.unregister_class(cls)
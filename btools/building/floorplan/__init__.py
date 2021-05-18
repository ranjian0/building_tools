import bpy

from .floorplan_ops import BTOOLS_OT_add_floorplan
from .floorplan_props import FloorplanProperty

classes = (FloorplanProperty, BTOOLS_OT_add_floorplan)

register_floorplan, unregister_floorplan = bpy.utils.register_classes_factory(classes)

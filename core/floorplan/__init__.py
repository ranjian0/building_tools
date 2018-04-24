import bpy

from .floorplan import Floorplan
from .floorplan_ops import FloorplanOperator
from .floorplan_props import FloorplanProperty

classes = (
    FloorplanProperty, FloorplanOperator
)

def register_floorplan():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_floorplan():
    for cls in classes:
        bpy.utils.unregister_class(cls)
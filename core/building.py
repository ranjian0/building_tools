import bpy
from bpy.props import *

from .floor import FloorProperty
from .floorplan import FloorplanProperty
from .door import DoorProperty
from .window import WindowProperty

class BuildingProperty(bpy.types.PropertyGroup):

    floorplan   = PointerProperty(type=FloorplanProperty)
    floors      = PointerProperty(type=FloorProperty)
    windows     = CollectionProperty(type=WindowProperty)
    doors       = CollectionProperty(type=DoorProperty)

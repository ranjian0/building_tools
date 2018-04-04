import bpy
from bpy.props import *

from .floor import FloorProperty
from .floorplan import FloorplanProperty
from .door import DoorProperty
from .window import WindowProperty

class BuildingProperty(bpy.types.PropertyGroup):
    """Master PropertyGroup to store all properties of a building"""

    floorplan   = PointerProperty(type=FloorplanProperty)
    floors      = PointerProperty(type=FloorProperty)
    windows     = CollectionProperty(type=WindowProperty)
    doors       = CollectionProperty(type=DoorProperty)

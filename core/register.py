import bpy
from bpy.props import (PointerProperty,
    CollectionProperty, IntProperty)

from .generic import SizeOffsetProperty

from .floor     import FloorOperator, FloorProperty
from .floorplan import FloorplanOperator, FloorplanProperty
from .door      import DoorOperator, DoorProperty
from .window    import WindowOperator, WindowProperty
from .rails     import RailOperator, RailProperty
from .balcony   import BalconyOperator, BalconyProperty
from .stairs    import StairsOperator, StairsProperty


# -- take care here -- ORDER MATTERS !!!
classes = [
    SizeOffsetProperty,

    FloorProperty, FloorOperator,
    FloorplanProperty, FloorplanOperator,
    DoorProperty, DoorOperator,
    WindowProperty, WindowOperator,
    RailProperty, RailOperator,
    BalconyProperty, BalconyOperator,
    StairsProperty, StairsOperator,
]


def register_core():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_core():
    for cls in classes:
        bpy.utils.unregister_class(cls)

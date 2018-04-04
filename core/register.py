import bpy
from bpy.props import (PointerProperty,
    CollectionProperty, IntProperty)

from .building import BuildingProperty
from .generic import (PropertyProxy,
    SplitProperty,RemovePropertyOperator)

from .floor     import FloorOperator, FloorProperty
from .floorplan import FloorplanOperator, FloorplanProperty
from .door      import DoorOperator, DoorProperty
from .window    import WindowOperator, WindowProperty


# -- take care here -- ORDER MATTERS !!!
classes = [
    SplitProperty,

    FloorOperator , FloorProperty,
    FloorplanOperator, FloorplanProperty,
    DoorOperator, DoorProperty,
    WindowOperator, WindowProperty,

    BuildingProperty, PropertyProxy,
    RemovePropertyOperator,
]


def register_core():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.building       = PointerProperty(type=BuildingProperty)
    bpy.types.Object.property_list  = CollectionProperty(type=PropertyProxy)
    bpy.types.Object.property_index = IntProperty()


def unregister_core():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Object.building
    del bpy.types.Object.property_list
    del bpy.types.Object.property_index

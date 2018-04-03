import bpy
from bpy.props import (PointerProperty,
    CollectionProperty, IntProperty)

from .generic import (PropertyProxy,
    BuildingProperty, SplitProperty,
    RemovePropertyOperator)

from .floor     import FloorOperator, FloorProperty
from .floorplan import FloorplanOperator, FloorplanProperty
from .door      import DoorOperator, DoorProperty
from .window    import WindowOperator, WindowProperty

classes = [
    FloorOperator , FloorProperty,
    FloorplanOperator, FloorplanProperty,
    DoorOperator, DoorProperty,
    WindowOperator, WindowProperty,

    BuildingProperty, PropertyProxy,
    SplitProperty, RemovePropertyOperator
]


def register_core():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.building       = PointerProperty(type=BuildingProperty)
    bpy.types.Object.property_list  = CollectionProperty(type=PropertyProxy)
    bpy.types.Object.property_index = IntProperty()


def unregister_core():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(cls.__name__, " :: --> ", e)

    del bpy.types.Object.building
    del bpy.types.Object.property_list
    del bpy.types.Object.property_index

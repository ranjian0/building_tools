import bpy

from .floor import FloorOperator, FloorProperty
from .floorplan import FloorplanOperator, FloorplanProperty

from .generic_props import PropertyProxy, BuildingProperty

classes = [
    FloorOperator , FloatProperty,
    FloorplanOperator, FloorplanProperty

]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.building = PointerProperty(type=BuildingProperty)

    bpy.types.Object.property_list = CollectionProperty(type=PropertyProxy)
    bpy.types.Object.property_index = IntProperty()


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Object.building
    del bpy.types.Object.property_list
    del bpy.types.Object.property_index

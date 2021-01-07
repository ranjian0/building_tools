import bpy
from .arch import ArchProperty
from .array import ArrayProperty
from .sizeoffset import SizeOffsetProperty

from .customobj import register_custom, unregister_custom
from .material import register_material, unregister_material
from .removegeom import register_removegeom, unregister_removegeom

from .balcony import register_balcony, unregister_balcony
from .door import register_door, unregister_door
from .fill import register_fill, unregister_fill
from .floor import register_floor, unregister_floor
from .floorplan import register_floorplan, unregister_floorplan
from .multigroup import register_multigroup, unregister_multigroup
from .railing import register_railing, unregister_railing
from .roof import register_roof, unregister_roof
from .stairs import register_stairs, unregister_stairs
from .window import register_window, unregister_window


classes = (
    ArchProperty,
    ArrayProperty,
    SizeOffsetProperty,
)

# -- ORDER MATTERS --
register_funcs = (
    register_custom,
    register_material,
    register_removegeom,

    register_railing,
    register_balcony,
    register_fill,
    register_door,
    register_floor,
    register_window,
    register_floorplan,
    register_stairs,
    register_roof,
    register_multigroup,
)

unregister_funcs = (
    unregister_custom,
    unregister_material,
    unregister_removegeom,

    unregister_railing,
    unregister_balcony,
    unregister_fill,
    unregister_door,
    unregister_floor,
    unregister_window,
    unregister_floorplan,
    unregister_stairs,
    unregister_roof,
    unregister_multigroup,
)


def register_building():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    for func in register_funcs:
        func()


def unregister_building():
    for func in unregister_funcs:
        func()

    for cls in classes:
        bpy.utils.unregister_class(cls)


import bpy
from .generic import SizeOffsetProperty

from .util_fill import register_fill, unregister_fill
from .util_rail import register_rail, unregister_rail

from .door      import register_door, unregister_door
from .floor     import register_floor, unregister_floor
from .window    import register_window, unregister_window
from .stairs    import register_stairs, unregister_stairs
from .balcony   import register_balcony, unregister_balcony
from .floorplan import register_floorplan, unregister_floorplan


# -- take care here -- ORDER MATTERS !!!
classes = [
    SizeOffsetProperty,
]

register_funcs = [
    register_fill,
    register_rail,

    register_door,
    register_floor,
    register_window,
    register_stairs,
    register_balcony,
    register_floorplan,
]

unregister_funcs = [
    unregister_fill,
    unregister_rail,

    unregister_door,
    unregister_floor,
    unregister_window,
    unregister_stairs,
    unregister_balcony,
    unregister_floorplan,
]


def register_core():
    for cls in classes:
        bpy.utils.register_class(cls)

    for func in register_funcs:
        func()


def unregister_core():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    for func in unregister_funcs:
        func()

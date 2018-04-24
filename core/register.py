import bpy
from .generic import SizeOffsetProperty

from .door      import register_door, unregister_door
from .rails     import register_rail, unregister_rail
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
    register_door,
    register_rail,
    register_floor,
    register_window,
    register_stairs,
    register_balcony,
    register_floorplan,
]

unregister_funcs = [
    unregister_door,
    unregister_rail,
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

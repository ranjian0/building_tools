import bpy

from .util_fill import register_fill, unregister_fill

from .door      import register_door, unregister_door
from .floor     import register_floor, unregister_floor
from .window    import register_window, unregister_window
from .floorplan import register_floorplan, unregister_floorplan
from .generic   import register_generic, unregister_generic

# -- take care here --
# -- ORDER MATTERS --

register_funcs = [
    register_generic,
    register_fill,

    register_door,
    register_floor,
    register_window,
    register_floorplan,
]

unregister_funcs = [
    unregister_generic,
    unregister_fill,

    unregister_door,
    unregister_floor,
    unregister_window,
    unregister_floorplan,
]


def register_core():
    for func in register_funcs:
        func()


def unregister_core():
    for func in unregister_funcs:
        func()

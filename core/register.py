from .fill import register_fill, unregister_fill
from .door import register_door, unregister_door
from .roof import register_roof, unregister_roof
from .rails import register_rail, unregister_rail
from .floor import register_floor, unregister_floor
from .stairs import register_stairs, unregister_stairs
from .window import register_window, unregister_window
from .balcony import register_balcony, unregister_balcony
from .generic import register_generic, unregister_generic
from .floorplan import register_floorplan, unregister_floorplan


# -- ORDER MATTERS --
register_funcs = (
    register_generic,
    register_fill,
    register_rail,
    register_door,
    register_floor,
    register_window,
    register_floorplan,
    register_balcony,
    register_stairs,
    register_roof,
)

unregister_funcs = (
    unregister_generic,
    unregister_fill,
    unregister_rail,
    unregister_door,
    unregister_floor,
    unregister_window,
    unregister_floorplan,
    unregister_balcony,
    unregister_stairs,
    unregister_roof,
)


def register_core():
    for func in register_funcs:
        func()


def unregister_core():
    for func in unregister_funcs:
        func()

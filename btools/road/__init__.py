from .road import register_road as reg_road, unregister_road as unreg_road
from .array import register_array, unregister_array

register_funcs = (
    reg_road,
    register_array,
)

unregister_funcs = (
    unreg_road,
    unregister_array,
)


def register_road():
    for func in register_funcs:
        func()


def unregister_road():
    for func in unregister_funcs:
        func()

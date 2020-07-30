from .road import register_road as r_road, unregister_road as un_road
from .array import register_array, unregister_array

register_funcs = (
    r_road,
    register_array,
)

unregister_funcs = (
    un_road,
    unregister_array,
)


def register_road():
    for func in register_funcs:
        func()


def unregister_road():
    for func in unregister_funcs:
        func()

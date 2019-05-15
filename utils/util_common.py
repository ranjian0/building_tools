import bpy
from mathutils import Vector


def equal(a, b, eps=0.001):
    """ Check if a and b are approximately equal with a margin of eps """
    return a == b or (abs(a - b) <= max(abs(a), abs(b)) * eps)


def clamp(value, minimum, maximum):
    """ Reset value between minimum and maximum """
    return max(min(value, maximum), minimum)


def condition(condition, value_true, value_false):
    """ Return value_true if condition is True else value_false """
    return value_true if condition else value_false


def ifeven(number, value_even, value_odd):
    """ Return value_even if number is an even number else value_odd """
    return condition(number % 2 == 0, value_even, value_odd)


def args_from_props(props, names):
    """ returns a tuple with the properties in props for the given names """
    return tuple(getattr(props, name) for name in names)


def kwargs_from_props(props):
    """ Converts all properties in a props{bpy.types.PropertyGroup} into dict """
    valid_types = (
        int,
        str,
        bool,
        float,
        tuple,
        Vector,
        bpy.types.Material,
        bpy.types.Object,
    )

    result = {}
    for p in dir(props):
        if p.startswith("__") or p in ["rna_type", "bl_rna"]:
            continue

        prop = getattr(props, p)
        if isinstance(prop, valid_types):
            result[p] = prop
        elif isinstance(prop, bpy.types.PropertyGroup) and not isinstance(
            prop, type(props)
        ):
            # property group within this property
            result.update(kwargs_from_props(prop))
    return result

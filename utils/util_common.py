import bpy
from mathutils import Vector


def equal(a, b, eps=0.001):
    """ Check if a and b are approximately equal with a margin of eps
    """
    return a == b or (abs(a - b) <= max(abs(a), abs(b)) * eps)


def clamp(value, minimum, maximum):
    """ Reset value between minimum and maximum
    """
    return max(min(value, maximum), minimum)


def condition(condition, value_true, value_false):
    """ Return value_true if condition is True else value_false
    """
    return value_true if condition else value_false


def ifeven(number, value_even, value_odd):
    """ Return value_even if number is an even number else value_odd
    """
    return condition(number % 2 == 0, value_even, value_odd)


def args_from_props(props, names):
    """ returns a tuple with the properties in props for the given names
    """
    return tuple(getattr(props, name) for name in names)


def kwargs_from_props(props):
    """ Converts all properties in a props{bpy.types.PropertyGroup} into dict
    """
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

def resitriced_size(parent_dimension, offset, size_min, size):
    """ Get size restricted by various factors
    """
    limit_x = min(parent_dimension[0] + 2*offset[0], parent_dimension[0] - 2*offset[0])
    limit_y = min(parent_dimension[1] + 2*offset[1], parent_dimension[1] - 2*offset[1])
    x = max(min(limit_x, size[0]), size_min[0])
    y = max(min(limit_y, size[1]), size_min[1])
    return x, y

def resitriced_offset(parent_dimension, size, offset):
    """ Get offset restricted by various factors
    """
    limit_x = (parent_dimension[0]-size[0])/2
    limit_y = (parent_dimension[1]-size[1])/2
    x = max(min(limit_x, offset[0]), -limit_x)
    y = max(min(limit_y, offset[1]), -limit_y)
    return x, y

import traceback

import bpy
import bmesh
from mathutils import Vector
from .util_constants import VEC_UP, VEC_RIGHT


def equal(a, b, eps=0.001):
    """ Check if a and b are approximately equal with a margin of eps
    """
    return a == b or (abs(a - b) <= eps)


def clamp(value, minimum, maximum):
    """ Reset value between minimum and maximum
    """
    return max(min(value, maximum), minimum)


def args_from_props(props, names):
    """ returns a tuple with the properties in props for the given names
    """
    return tuple(getattr(props, name) for name in names)


def popup_message(message, title="Error", icon="ERROR"):
    def oops(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(oops, title=title, icon=icon)


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


def crash_safe(func):
    """ Decorator to handle exceptions in bpy Operators safely
    """

    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            popup_message("See console for errors", title="Operator Failed!")
            traceback.print_exc()

            # -- cleanup blender context
            if bpy.context.mode == "EDIT_MESH":
                bmesh.update_edit_mesh(bpy.context.edit_object.data, True)

            # -- exit operator
            return {"CANCELLED"}

    return inner


def restricted_size(parent_dimensions, offset, size_min, size):
    """ Get size restricted by various factors
    """
    limit_x = min(parent_dimensions[0] + 2 * offset[0], parent_dimensions[0] - 2 * offset[0])
    limit_y = min(parent_dimensions[1] + 2 * offset[1], parent_dimensions[1] - 2 * offset[1])
    x = clamp(size[0], size_min[0], limit_x)
    y = clamp(size[1], size_min[1], limit_y)
    return x, y


def restricted_offset(parent_dimensions, size, offset):
    """ Get offset restricted by various factors
    """
    limit_x = (parent_dimensions[0] - size[0]) / 2
    limit_y = (parent_dimensions[1] - size[1]) / 2
    x = clamp(offset[0], -limit_x, limit_x)
    y = clamp(offset[1], -limit_y, limit_y)
    return x, y


def local_to_global(face, vec):
    """ Convert vector from local to global space, considering face normal as local z and world z as local y
    """
    x, y, z = local_xyz(face)
    global_offset = (x * vec.x) + (y * vec.y) + (z * vec.z)
    return global_offset


def local_xyz(face):
    """ Get local xyz directions
    """
    z = face.normal.copy()
    x = z.cross(VEC_RIGHT if z.to_tuple(1) == VEC_UP.to_tuple(1) else VEC_UP)
    y = x.cross(z)
    return x, y, z

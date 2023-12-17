import bpy
import enum
import bmesh
import traceback
from mathutils import Vector
from bpy.props import PointerProperty
from .util_constants import VEC_UP, VEC_RIGHT


def equal(a, b, eps=0.001):
    """Check if a and b are approximately equal with a margin of eps"""
    return a == b or (abs(a - b) <= eps)


def clamp(value, minimum, maximum):
    """Reset value between minimum and maximum"""
    return max(min(value, maximum), minimum)


def minmax(items, key=lambda val: val):
    """Return the smallest and largest value in items using key"""
    _min = _max = None
    for val in items:
        if _min is None or key(val) < key(_min):
            _min = val
        if _max is None or key(val) > key(_max):
            _max = val
    return _min, _max


def args_from_props(props, names):
    """returns a tuple with the properties in props for the given names"""
    return tuple(getattr(props, name) for name in names)


def popup_message(message, title="Error", icon="ERROR"):
    def oops(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(oops, title=title, icon=icon)


def prop_from_dict(prop, dictprop):
    """Set all values in prop from dictprop"""
    for k, v in dictprop.items():
        if hasattr(prop, k):
            if isinstance(v, enum.Enum):
                v = v.value
            try:
                setattr(prop, k, v)
            except AttributeError:
                # inner pointer prop
                inner_prop = getattr(prop, k)
                prop_from_dict(inner_prop, v)


def dict_from_prop(prop):
    """Converts all properties in a prop{bpy.types.PropertyGroup} into dict"""
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
    for p in dir(prop):
        if p.startswith("__") or p in ["rna_type", "bl_rna"]:
            continue

        if not hasattr(prop, p):
            continue

        pn = getattr(prop, p)
        if isinstance(pn, valid_types):
            result[p] = pn
        elif isinstance(pn, bpy.types.PropertyGroup) and not isinstance(pn, type(prop)):
            # property group within this property
            result.update(dict_from_prop(pn))
    return result


def crash_safe(func):
    """Decorator to handle exceptions in bpy Operators safely"""

    def crash_handler(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            popup_message("See console for errors", title="Operator Failed!")
            traceback.print_exc()

            # -- cleanup blender context
            if bpy.context.mode == "EDIT_MESH":
                bmesh.update_edit_mesh(
                    bpy.context.edit_object.data, loop_triangles=True
                )

            # -- exit operator
            return {"CANCELLED"}

    return crash_handler


def restricted_size(parent_dimensions, offset, size_min, size):
    """Get size restricted by various factors"""
    limit_x = min(
        parent_dimensions[0] + 2 * offset[0], parent_dimensions[0] - 2 * offset[0]
    )
    limit_y = min(
        parent_dimensions[1] + 2 * offset[1], parent_dimensions[1] - 2 * offset[1]
    )
    x = clamp(size[0], size_min[0], limit_x)
    y = clamp(size[1], size_min[1], limit_y)
    return x, y


def restricted_offset(parent_dimensions, size, offset):
    """Get offset restricted by various factors"""
    limit_x = (parent_dimensions[0] - size[0]) / 2
    limit_y = (parent_dimensions[1] - size[1]) / 2
    x = clamp(offset[0], -limit_x, limit_x)
    y = clamp(offset[1], -limit_y, limit_y)
    return x, y


def local_to_global(face, vec):
    """Convert vector from local to global space, considering face normal as local z and world z as local y"""
    x, y, z = local_xyz(face)
    global_offset = (x * vec.x) + (y * vec.y) + (z * vec.z)
    return global_offset


def local_xyz(face):
    """Get local xyz directions"""
    z = face.normal.copy()
    x = z.cross(VEC_RIGHT if z.to_tuple(1) == VEC_UP.to_tuple(1) else VEC_UP)
    y = x.cross(z)
    return x, y, z


def XYDir(vec):
    """Remove the z component from a vector and normalize"""
    vec.z = 0
    return vec.normalized()


def get_scaled_unit(value):
    """Mostly to scale prop values to current scene unit scale"""
    try:
        scale = bpy.context.scene.unit_settings.scale_length
    except AttributeError:
        # Addon Registration, context.scene is not available
        scale = 1.0
    return value / scale


def get_defaults(prop):
    defaults = dict()
    for name, data in prop.__annotations__.items():
        if data.function == PointerProperty:
            defaults[name] = get_defaults(getattr(prop, name))
        else:
            defaults[name] = data.keywords.get("default")

    for name in list(defaults.keys()):
        data = defaults[name]
        if isinstance(data, dict):
            for k, v in data.items():
                defaults[f"{name}.{k}"] = v
            del defaults[name]
    return defaults


def set_defaults(prop):
    defaults = get_defaults(prop)
    for name, value in defaults.items():
        setattr(prop, name, value)

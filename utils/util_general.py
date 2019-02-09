import bpy
from mathutils import Vector


def equal(a, b, eps=0.001):
    """ Check if a and b are approximately equal with a margin of eps """
    return a == b or (abs(a-b) <= max(abs(a), abs(b)) * eps)

def clamp(val, _min, _max):
    """ Reset val between _min and __max """
    return max(min(val, _max), _min)

def condition(con, val1, val2):
    """ Return val1 if con is true else val2 """
    return val1 if con else val2

def ifeven(num, val1, val2):
    """ Return val1 if num is an even number else val2 """
    return condition(num % 2 == 0, val1, val2)

def args_from_props(props, names):
    """ returns a tuple with the properties in props for the given names """
    return tuple(getattr(props, name) for name in names)

def kwargs_from_props(props):
    """ Converts all properties in a props{bpy.types.PropertyGroup} into dict """
    valid_types = (
        int, float, str, tuple, bool, Vector,
        bpy.types.Material,
        bpy.types.Object
        )

    result = {}
    for p in dir(props):
        if p.startswith('__') or p in ['rna_type', 'bl_rna']:
            continue
        prop = getattr(props, p)

        if isinstance(prop, valid_types):
            result[p] = prop
        elif isinstance(prop, bpy.types.PropertyGroup) and not isinstance(prop, type(props)):
            # property group within this property
            result.update(kwargs_from_props(prop))
    return result

def assert_test(func):
    """ Catch any Exceptions that may occur in test func """

    def wrapper():
        try:
            func()
            print(func.__name__.upper() + " PASSED ..")
        except Exception as e:
            print(func.__name__.upper() + " FAILED .. :", e)

    return wrapper

def clean_scene():
    """ Delete all objects in the scene if any """
    scene = bpy.context.scene

    if scene.objects:
        active = scene.objects.active
        if active and active.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
    return scene

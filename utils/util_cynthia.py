import bpy
from mathutils import Vector


def condition(con, val1, val2):
    """ Return val1 if con is true else val2 """
    return val1 if con else val2


def ifeven(num, val1, val2):
    """ Return val1 if num is an even number else val2 """
    return condition(num % 2 == 0, val1, val2)


def kwargs_from_props(props):
    """ Converts all properties in a props into dict """
    result = {}
    for p in dir(props):
        if p.startswith('__'):
            continue
        prop = getattr(props, p)
        if isinstance(prop, (int, float, str, tuple, bool, Vector)):
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

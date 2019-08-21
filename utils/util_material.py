import bpy
import bmesh
from enum import Enum
from functools import wraps

from .util_object import bm_from_obj, bm_to_obj


class FaceGroups(Enum):
    SLAB = 0
    WALL = 1


def facegroup(group):
    def outer(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            bm = [arg for arg in args if isinstance(arg, bmesh.types.BMesh)].pop()
            faces = set(bm.faces)

            func(*args, **kwargs)

            new_faces = set(bm.faces) - faces
            add_faces_to_group(bm, new_faces, group)
        return wrapper
    return outer


def add_faces_to_group(bm, faces, group):
    face_map = bm.faces.layers.face_map.active
    for face in faces:
        face[face_map] = group.value


def create_face_maps_for_object(obj):
    # -- verify face map
    bm = bm_from_obj(obj)
    bm.faces.layers.face_map.verify()
    bm_to_obj(bm, obj)

    # -- add face maps
    for group in FaceGroups:
        obj.face_maps.new(name=group.name.lower())


DEFAULT_MATERIALS = {
    "mat_slab": (0.208, 0.183, 0.157),
    "mat_wall": (0.190, 0.117, 0.04),
    "mat_window_frame": (0.8, 0.8, 0.8),
    "mat_window_pane": (0, 0.6, 0),
    "mat_window_bars": (0, 0.7, 0),
    "mat_window_glass": (0, 0.1, 0.6),
    "mat_door_frame": (0.8, 0.8, 0.8),
    "mat_door_pane": (0.13, 0.05, 0),
    "mat_door_groove": (0.13, 0.05, 0),
    "mat_door_glass": (0, 0.1, 0.6),
}


def create_material(obj, name):
    """ Create a material with name, and link to the obj
    """
    if has_material(obj, name):
        return

    if name in bpy.data.materials.keys():
        mat = bpy.data.materials[name]
        link_material(obj, mat)
        return

    mat = bpy.data.materials.new(obj.name + "_" + name)
    mat.diffuse_color = DEFAULT_MATERIALS.get(name, (0, 0, 0)) + (1,)
    mat.use_nodes = True
    link_material(obj, mat)


def link_material(obj, mat):
    """ link material mat to obj
    """
    if not has_material(obj, mat.name):
        obj.data.materials.append(mat)


def has_material(obj, name):
    """ check if obj has a material with name
    """
    return name in obj.data.materials.keys()


def set_material(faces, mat_enum):
    """ Set the material id of faces to the matertial mat_enum
    """
    name = mat_enum.value
    obj = bpy.context.object
    if obj is None:
        return

    mat_idx = -1
    create_material(obj, name)
    for i, mat in enumerate(obj.data.materials):
        if name in mat.name:
            mat_idx = i
            break

    for f in faces:
        f.material_index = mat_idx

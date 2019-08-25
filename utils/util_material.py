import bpy
import bmesh
from enum import Enum, auto
from functools import wraps

from .util_mesh import get_edit_mesh


class AutoIndex(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return count


class FaceMap(AutoIndex):
    """ Enum provides names for face_maps """

    SLABS = auto()
    WALLS = auto()

    WINDOW = auto()
    WINDOW_BARS = auto()
    WINDOW_PANES = auto()
    WINDOW_FRAMES = auto()
    WINDOW_LOUVERS = auto()

    DOOR = auto
    DOOR_PANES = auto()
    DOOR_PANELS = auto()
    DOOR_FRAMES = auto()
    DOOR_LOUVERS = auto()

    BALCONY = auto()
    BALCONY_RAILING_POSTS = auto()
    BALCONY_RAILING_WALLS = auto()
    BALCONY_RAILING_RAILS = auto()

    STAIRS = auto()
    STAIRS_RAILING_POSTS = auto()
    STAIRS_RAILING_WALLS = auto()
    STAIRS_RAILING_RAILS = auto()


def map_new_faces(group, skip=None):
    """ Finds all newly created faces in a function and adds them to a face_map
        called group.name.lower()

        if skip is provided, then all faces in the face_map called skip.name
        will not be added to the face_map
    """

    def outer(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            bm = [arg for arg in args if isinstance(arg, bmesh.types.BMesh)].pop()
            faces = set(bm.faces)

            result = func(*args, **kwargs)

            new_faces = set(bm.faces) - faces
            add_faces_to_map(bm, list(new_faces), group, skip)
            return result

        return wrapper

    return outer


def add_faces_to_map(bm, faces, group, skip=None):
    """ Sets the face_map index of faces to the index of the face_map called
        group.name.lower()

        see map_new_faces for the option *skip*
    """
    face_map = bm.faces.layers.face_map.active
    group_index = face_map_index_from_name(group.name.lower())

    def remove_skipped(f):
        if skip:
            skip_index = face_map_index_from_name(skip.name.lower())
            return not (f[face_map] == skip_index)
        return True

    for face in list(filter(remove_skipped, faces)):
        face[face_map] = group_index


def add_facemap_for_groups(groups):
    """ Creates a face_map called group.name.lower if none exists
        in the active object
    """
    obj = bpy.context.object
    groups = groups if isinstance(groups, (list, tuple)) else [groups]

    for group in groups:
        if not obj.face_maps.get(group.name.lower()):
            obj.face_maps.new(name=group.name.lower())


def verify_facemaps_for_object(obj):
    """ Ensure object has a facemap layer """
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    bm.faces.layers.face_map.verify()
    bmesh.update_edit_mesh(me, True)


def face_map_index_from_name(name):
    for _, fmap in bpy.context.object.face_maps.items():
        if fmap.name == name:
            return fmap.index
    return -1


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

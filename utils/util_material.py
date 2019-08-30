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

    STAIRS = auto()
    BALCONY = auto()

    RAILING_POSTS = auto()
    RAILING_WALLS = auto()
    RAILING_RAILS = auto()

    ROOF = auto()
    ROOF_HANGS = auto()


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
            obj.facemap_materials.add()


def verify_facemaps_for_object(obj):
    """ Ensure object has a facemap layer """
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    bm.faces.layers.face_map.verify()
    bmesh.update_edit_mesh(me, True)


def set_material_for_active_facemap(material, context):
    obj = context.object
    index = obj.face_maps.active_index
    active_facemap = obj.face_maps[index]

    link_material(obj, material)
    mat_id = [
        idx for idx, mat in enumerate(obj.data.materials) if mat == material
    ].pop()

    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    face_map = bm.faces.layers.face_map.active
    for face in bm.faces:
        if face[face_map] == active_facemap.index:
            face.material_index = mat_id

    bmesh.update_edit_mesh(me, True)


def face_map_index_from_name(name):
    for _, fmap in bpy.context.object.face_maps.items():
        if fmap.name == name:
            return fmap.index
    return -1


def link_material(obj, mat):
    """ link material mat to obj
    """
    if not has_material(obj, mat.name):
        obj.data.materials.append(mat)


def has_material(obj, name):
    """ check if obj has a material with name
    """
    return name in obj.data.materials.keys()

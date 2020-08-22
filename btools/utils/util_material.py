from enum import Enum, auto
from functools import wraps

import bmesh
import bpy

from .util_mesh import get_edit_mesh
from .util_object import bmesh_from_active_object


class AutoIndex(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return count


class FaceMap(AutoIndex):
    """ Enum provides names for face_maps """

    # Buildings
    SLABS = auto()
    WALLS = auto()
    COLUMNS = auto()

    FRAME = auto()

    WINDOW = auto()
    WINDOW_BARS = auto()
    WINDOW_PANES = auto()
    WINDOW_LOUVERS = auto()

    DOOR = auto
    DOOR_PANES = auto()
    DOOR_PANELS = auto()
    DOOR_LOUVERS = auto()

    STAIRS = auto()
    BALCONY = auto()

    RAILING_POSTS = auto()
    RAILING_WALLS = auto()
    RAILING_RAILS = auto()

    ROOF = auto()
    ROOF_HANGS = auto()

    # Roads
    ROAD = auto()
    SHOULDER = auto()
    SIDEWALK = auto()
    SIDEWALK_SIDE = auto()
    SHOULDER_EXTENSION = auto()


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

    obj = bpy.context.object

    # -- if auto uv map is set, perform UV Mapping for given faces
    if obj.facemap_materials[group_index].auto_map:
        map_method = obj.facemap_materials[group_index].uv_mapping_method
        uv_map_active_editmesh_selection(faces, map_method)

    # -- if the facemap already has a material assigned, assign the new faces to the material
    mat = obj.facemap_materials[group_index].material
    mat_id = [idx for idx, m in enumerate(obj.data.materials) if m == mat]
    if mat_id:
        for f in faces:
            f.material_index = mat_id[-1]


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

    with bmesh_from_active_object(context) as bm:

        face_map = bm.faces.layers.face_map.active
        for face in bm.faces:
            if face[face_map] == active_facemap.index:
                face.material_index = mat_id


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


def create_object_material(obj, mat_name):
    """ Create a new material and link it to the given object
    """
    if not has_material(obj, mat_name):
        if bpy.data.materials.get(mat_name, None):
            # XXX if material with this name already exists in another object
            # append the object name to this material name
            mat_name += ".{}".format(obj.name)

        mat = bpy.data.materials.new(mat_name)
        link_material(obj, mat)
        return mat
    return obj.data.materials.get(mat_name)


def uv_map_active_editmesh_selection(faces, method):
    # -- ensure we are in editmode
    if not bpy.context.object.mode == "EDIT":
        return

    # -- if faces are not selected, do selection
    selection_state = [f.select for f in faces]
    for f in faces:
        f.select_set(True)

    # -- perform mapping
    if method == "UNWRAP":
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
    elif method == "CUBE_PROJECTION":
        bpy.ops.uv.cube_project(cube_size=0.5)

    # -- restore previous selection state
    for f, sel in zip(faces, selection_state):
        f.select_set(sel)

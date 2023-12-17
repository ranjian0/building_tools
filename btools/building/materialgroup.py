import bpy
import bmesh

from enum import Enum, auto
from functools import wraps

from ..utils import (
    link_material,
    bmesh_from_active_object,
    uv_map_active_editmesh_selection,
)


class AutoIndex(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return count


class MaterialGroup(AutoIndex):
    """Enum provides names for material group"""

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

    CUSTOM = auto()

    # Roads
    ROAD = auto()
    SHOULDER = auto()
    SIDEWALK = auto()
    SIDEWALK_SIDE = auto()
    SHOULDER_EXTENSION = auto()


def map_new_faces(group, skip=None):
    """Finds all newly created faces in a function and adds them to a material group
    called group.name.lower()

    if skip is provided, then all faces in the matgroup called skip.name
    will not be added to the matgroup
    """

    def outer(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            bm = [arg for arg in args if isinstance(arg, bmesh.types.BMesh)].pop()
            faces = set(bm.faces)

            result = func(*args, **kwargs)

            new_faces = set(bm.faces) - faces
            add_faces_to_group(bm, list(new_faces), group, skip)
            return result

        return wrapper

    return outer


def add_faces_to_group(bm, faces, group, skip=None):
    """Sets the attribute index of faces to the index of the material group called
    group.name.lower()

    see map_new_faces for the option *skip*
    """
    obj = bpy.context.object
    layer = bm.faces.layers.int.get(".bt_material_group_index")
    matgroup = [mt for mt in obj.bt_materials if mt.name == group.name.lower()]
    if not matgroup:
        add_material_group(group)
        matgroup = [mt for mt in obj.bt_materials if mt.name == group.name.lower()].pop()
    else:
        matgroup = matgroup.pop()
    
    group_index = matgroup.index
    def remove_skipped(f):
        if skip:
            matgroup_skip = [mt for mt in obj.bt_materials if mt.name == skip.name.lower()].pop()
            matgroup_skip_index = matgroup_skip.index
            return not (f[layer] == matgroup_skip_index)
        return True

    for face in list(filter(remove_skipped, faces)):
        face[layer] = group_index

    
    if group_index >= len(obj.bt_materials):
        # Layout of the material groups was destroyed eg through an operation like object join.
        # User on their own for now.
        # TODO(ranjian0) possible solution would be to rebuild the matgroup every time this branch is reached.
        return

    # -- if auto uv map is set, perform UV Mapping for given faces
    if obj.bt_materials[group_index].auto_map:
        map_method = obj.bt_materials[group_index].uv_mapping_method
        uv_map_active_editmesh_selection(faces, map_method)

    # -- if the group already has a material assigned, assign the new faces to the material
    mat = obj.bt_materials[group_index].material
    mat_id = [idx for idx, m in enumerate(obj.data.materials) if m == mat]
    if mat_id:
        for f in faces:
            f.material_index = mat_id[-1]


def add_material_group(groups):
    """Creates a matgroup called group.name.lower if none exists
    in the active object
    """
    obj = bpy.context.object
    groups = groups if isinstance(groups, (list, tuple)) else [groups]

    for group in groups:
        mat_groups = [mt.name for mt in obj.bt_materials]
        if group.name.lower() not in mat_groups:
            mt = obj.bt_materials.add()
            mt.name = group.name.lower()
            mt.index = len(obj.bt_materials) - 1


def verify_matgroup_attribute_for_object(obj):
    """Ensure object has a btools material attribute"""
    obj.data.attributes.new(
        name=".bt_material_group_index",
        type="INT",
        domain="FACE")


def set_material_for_active_matgroup(material, context):
    """Set `material` on all the faces for the current/active material group"""
    obj = context.object
    index = obj.bt_materials_active_index
    matgroup = obj.bt_materials[index]
    

    link_material(obj, material)
    mat_id = [
        idx for idx, mat in enumerate(obj.data.materials) if mat == material
    ].pop()

    with bmesh_from_active_object(context) as bm:
        layer = bm.faces.layers.int.get(".bt_material_group_index")
        for face in bm.faces:
            if face[layer] == matgroup.index:
                face.material_index = mat_id


def clear_material_for_active_matgroup(context):
    """Remove the material on all faces for the current/active matgroup"""
    obj = context.object
    matgroup = obj.bt_materials[obj.bt_materials_active_index]

    with bmesh_from_active_object(context) as bm:
        layer = bm.faces.layers.int.get(".bt_material_group_index")
        for face in bm.faces:
            if face[layer] == matgroup.index:
                face.material_index = 0


def clear_empty_matgroups(context):
    """Remove all groups that don't have any faces assigned"""
    obj = context.object
    with bmesh_from_active_object(context) as bm:
        layer = bm.faces.layers.int.get(".bt_material_group_index")
        used_indices = {f[layer] for f in bm.faces}
        all_indices = {m.index for m in obj.bt_materials}
        tag_remove_indices = all_indices - used_indices

        # -- remove groups in reverse order
        for idx in reversed(list(tag_remove_indices)):
            obj.bt_materials.remove(idx)


def find_faces_without_matgroup(bm):
    """Find all the faces in bm that don't belong to any matgroup"""
    result = []

    layer = bm.faces.layers.int.get(".bt_material_group_index")
    for f in bm.faces:
        if f[layer] < 0:
            result.append(f)
    return result

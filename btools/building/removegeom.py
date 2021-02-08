import bpy
import math
import bmesh
from .facemap import FaceMap, add_faces_to_map
from ..utils import (
    minmax,
    select,
    VEC_UP,
    VEC_DOWN,
    sort_faces,
    sort_verts,
    get_edit_mesh,
)


def remove(context):
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    bound_faces = get_faces_in_selection_bounds(bm)
    cornerv, midv = get_bounding_verts(bound_faces)

    bmesh.ops.delete(bm, geom=bound_faces, context="FACES")
    bmesh.ops.dissolve_verts(bm, verts=midv)
    newfaces = bmesh.ops.contextual_create(bm, geom=cornerv).get('faces')
    add_faces_to_map(bm, newfaces, FaceMap.WALLS)

    bmesh.update_edit_mesh(me, True)


def get_faces_in_selection_bounds(bm):
    """Determine all faces that lie within the bounds of selected faces"""
    faces = [f for f in bm.faces if f.select]

    normal = faces[0].normal.copy()
    L, R = normal.cross(VEC_UP), normal.cross(VEC_DOWN)
    faces = sort_faces(faces, R)
    start, finish = faces[0].calc_center_median(), faces[-1].calc_center_median()

    faces_left = filter(lambda f: L.dot(f.calc_center_median()) < L.dot(start), bm.faces)
    faces_mid = filter(lambda f: R.dot(f.calc_center_median()) < R.dot(finish), faces_left)
    valid_normals = [normal.to_tuple(2), L.to_tuple(2), R.to_tuple(2), VEC_UP.to_tuple(2), VEC_DOWN.to_tuple(2)]
    faces_correct_normal = filter(lambda f: f.normal.to_tuple(2) in valid_normals, faces_mid)

    def calc_face_bounds_dist(f):
        vts = sort_verts(f.verts, R)
        return (vts[0].co - vts[-1].co).length

    bounds_distance = (start - finish).length
    faces_within_distance = filter(
        lambda f: calc_face_bounds_dist(f) < bounds_distance,
        faces_correct_normal
    )

    select(faces, False)
    return list(faces_within_distance) + faces


def get_bounding_verts(faces):
    """Get the extreme edges and verts in the faces"""
    verts = list({v for f in faces for v in f.verts})
    edges = list({e for f in faces for e in f.edges})
    min_z, max_z = minmax(verts, key=lambda v: v.co.z)
    bound_verts = [v for v in verts if v.co.z == max_z.co.z or v.co.z == min_z.co.z]

    corner_verts, mid_verts = [], []
    for v in bound_verts:
        angle = vert_angle(v, edges)
        if angle == 0:
            mid_verts.append(v)
            continue
        corner_verts.append(v)

    return corner_verts, mid_verts


def vert_angle(v, filter_edges):
    ve = [e for e in v.link_edges if e in filter_edges]
    if len(ve) > 2:
        return 0

    vecs = [v.co - e.other_vert(v).co for e in ve]
    return vecs[0].angle(vecs[1])


class BTOOLS_OT_remove_geom(bpy.types.Operator):
    """Remove building tools geometry from selected faces"""

    bl_idname = "btools.remove_geom"
    bl_label = "Clear Geometry"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        remove(context)
        return {"FINISHED"}


classes = (BTOOLS_OT_remove_geom,)


def register_removegeom():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_removegeom():
    for cls in classes:
        bpy.utils.unregister_class(cls)

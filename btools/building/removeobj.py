import bpy
import math
import bmesh
from ..utils import (
    minmax, 
    select,
    VEC_UP,
    get_edit_mesh, 
    calc_faces_median
)

def remove(context):
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    bound_faces = get_faces_in_selection_bounds(bm)
    cornerv, midv = get_bounding_verts(bound_faces)

    bmesh.ops.delete(bm, geom=bound_faces, context="FACES")
    bmesh.ops.dissolve_verts(bm, verts=midv)
    bmesh.ops.contextual_create(bm, geom=cornerv)

    bmesh.update_edit_mesh(me, True)

def get_faces_in_selection_bounds(bm):
    """ Determine all faces that lie within the bounds of selected faces
    """
    faces = [f for f in bm.faces if f.select]
    verts = list({v for f in faces for v in f.verts})

    normal = faces[0].normal.copy()
    medianf = calc_faces_median(faces)
    min_z, max_z = minmax(verts, key=lambda v:v.co.z)
    max_dist = max([(f.calc_center_median() - medianf).length for f in faces])

    close_faces = []
    for f in bm.faces:
        if f in faces:
            continue

        cm = f.calc_center_median()
        within_median = (cm - medianf).length_squared <= max_dist**2
        within_angle = math.radians(85.0) <= (medianf - cm).angle(normal) <= math.radians(95.0)
        within_height = round(cm.z, 4) > round(min_z.co.z, 4) and round(cm.z, 4) < round(max_z.co.z, 4)
        if within_angle and within_median and within_height:
            close_faces.append(f)

    select(faces, False)
    return close_faces + faces

def get_bounding_verts(faces):
    """ Get the extreme edges and verts in the faces
    """
    verts = list({v for f in faces for v in f.verts})
    edges = list({e for f in faces for e in f.edges})
    min_z, max_z = minmax(verts, key=lambda v:v.co.z)
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


class BTOOLS_OT_remove_obj(bpy.types.Operator):
    """Remove building tools geometry from selected faces"""

    bl_idname = "btools.remove_obj"
    bl_label = "Clear Geometry"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        remove(context)
        return {"FINISHED"}

classes = (BTOOLS_OT_remove_obj, )

def register_removeobj():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_removeobj():
    for cls in classes:
        bpy.utils.unregister_class(cls)

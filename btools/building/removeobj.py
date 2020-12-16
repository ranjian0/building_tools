"""
Small Operator to remove components from a set of faces
"""
import bpy
import bmesh
from ..utils import get_edit_mesh, minmax, select

def remove(context):
    # -- get selection
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    faces = [f for f in bm.faces if f.select]
    verts = list({v for f in faces for v in f.verts})

    # -- find bounding verts from face selection
    min_x, max_x = minmax(verts, key=lambda v:v.co.x)
    min_y, max_y = minmax(verts, key=lambda v:v.co.y)
    min_z, max_z = minmax(verts, key=lambda v:v.co.z)

    def in_range(v, _min, _max, attr="x"):
        return getattr(_min.co, attr) <= getattr(v.co, attr) <= getattr(_max.co, attr)

    verts_in_x = list(filter(lambda v:in_range(v, min_x, max_x), bm.verts))
    verts_in_y = list(filter(lambda v:in_range(v, min_y, max_y, "y"), bm.verts))
    verts_in_z = list(filter(lambda v:in_range(v, min_z, max_z, "z"), bm.verts))

    bound_verts = list(set(verts_in_x) & set(verts_in_y) & set(verts_in_z))
    # select(faces, False)
    # select(bound_verts)

    # if (max_x.x - min_x.x) < 0.1:
    #     print("oops x")
    # select(faces, False)
    # select([max_z, min_z])
    # print(max_x, min_x)
    # select([min_x, min_y, min_z, max_x, max_y, max_z])
    # print("Done Selection")
    # print(min_x, max_x)
    # print(min_y, max_y)
    # print(min_z, max_z) 

    # -- validate selection (select extra neighbouring faces that user may not have selected)
    # for v in verts:
    #     for f in v.link_faces:
    #         if all(vl in verts for vl in f.verts):
    #             # -- this face is linked to the current selection
    #             if not f.select:
    #                 print("FOund ", f.normal)
    #                 f.select_set(True)

    # -- selection bounds
    # sorted
    # print(faces)
    bmesh.update_edit_mesh(me, True)


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

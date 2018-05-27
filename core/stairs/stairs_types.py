import bmesh
from mathutils import Vector
from bmesh.types import BMVert, BMEdge

from ...utils import (
    split,
    split_quad,
    filter_geom,
    get_edit_mesh,
    face_with_verts,
    calc_edge_median,
    filter_vertical_edges,
    filter_horizontal_edges
    )

def make_stairs(step_count, step_width, landing, landing_width, **kwargs):
    """Extrude steps from selected faces

    Args:
        step_count (int): Number of stair steps
        step_width (float): width of each stair step
        **kwargs: Extra kwargs from StairsProperty
    """

    # Get current edit mesh
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    # Find selected face
    faces = [f for f in bm.faces if f.select]

    for f in faces:
        n = f.normal
        f.select = False

        # Perform split
        f = make_stair_split(bm, f, **kwargs)
        if not f:
            return

        _key = lambda v : v.co.z
        fheight =  max(f.verts, key=_key).co.z - min(f.verts, key=_key).co.z

        ext_face = f
        for i in range(step_count):
            # extrude face
            ret_face = bmesh.ops.extrude_discrete_faces(bm,
                faces=[ext_face]).get('faces')[-1]

            bmesh.ops.translate(bm, vec=n * step_width,
                verts=ret_face.verts)


            if i < (step_count-1):
                # cut step height
                res = split_quad(bm, ret_face, False, 1)
                bmesh.ops.translate(bm,
                    verts=filter_geom(res['geom_inner'], BMVert),
                    vec=(0, 0, (fheight/2)-(fheight/(step_count-i))))

                # update ext_face
                ext_face = min([f for f in filter_geom(res['geom_inner'], BMVert)[-1].link_faces],
                    key=lambda f: f.calc_center_median().z)

    bmesh.update_edit_mesh(me, True)

def make_stair_split(bm, face, size, off, **kwargs):
    """Use properties from SplitOffset to subdivide face into regular quads

    Args:
        bm   (bmesh.types.BMesh):  bmesh for current edit mesh
        face (bmesh.types.BMFace): face to make split (must be quad)
        size (vector2): proportion of the new face to old face
        off  (vector3): how much to offset new face from center
        **kwargs: Extra kwargs from WindowProperty

    Returns:
        bmesh.types.BMFace: New face created after split
    """
    return split(bm, face, size.y, size.x, off.x, off.y, off.z)


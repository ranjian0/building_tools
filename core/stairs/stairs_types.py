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

def make_stairs(step_count, step_width, landing, landing_width, stair_direction, **kwargs):
    """Extrude steps from selected faces

    Args:
        step_count (int): Number of stair steps
        step_width (float): width of each stair step
        landing (bool): Whether the stairs have a landing
        landing_width (float): Width of the landing if any
        **kwargs: Extra kwargs from StairsProperty

    """

    # Get current edit mesh
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    # Find selected face
    faces = [f for f in bm.faces if f.select]

    for f in faces:
        f.select = False

        # Perform split
        f = make_stair_split(bm, f, **kwargs)
        if not f:
            return

        _key = lambda v : v.co.z
        fheight =  max(f.verts, key=_key).co.z - min(f.verts, key=_key).co.z

        ext_face = f
        top_faces = []
        for i in range(step_count):
            # extrude face
            n = ext_face.normal
            ext_width = landing_width if (landing and i==0) else step_width
            ret_face = bmesh.ops.extrude_discrete_faces(bm,
                faces=[ext_face]).get('faces')[-1]

            bmesh.ops.translate(bm, vec=n * ext_width,
                verts=ret_face.verts)

            # -- keep reference to top faces for railing
            top_faces.append(filter(lambda f:f.normal.z,
                list({f for e in ret_face.edges for f in e.link_faces})))

            if landing and i == 0:
                # adjust ret_face based on stair direction

                # determine left/right faces
                fnormal_filter = {
                    # normal        left      right
                    ( 0, 1, 0) : [(-1, 0, 0), ( 1, 0, 0)],
                    ( 0,-1, 0) : [( 1, 0, 0), (-1, 0, 0)],
                    ( 1, 0, 0) : [( 0, 1, 0), ( 0,-1, 0)],
                    (-1, 0, 0) : [( 0,-1, 0), ( 0, 1, 0)]
                }

                valid_faces = list(filter(
                    lambda f : f.normal.to_tuple(1) in fnormal_filter[ret_face.normal.to_tuple(1)],
                    list({f for e in ret_face.edges for f in e.link_faces}))
                )

                left, right = valid_faces
                # set appropriate face for next extrusion
                if stair_direction == 'FRONT':
                    pass
                elif stair_direction == 'LEFT':
                    ret_face = left
                elif stair_direction == 'RIGHT':
                    ret_face = right

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


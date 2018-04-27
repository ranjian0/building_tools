import bmesh
from bmesh.types import BMVert, BMEdge
from mathutils import Vector

from ...utils import (
    split_quad,
    filter_geom,
    get_edit_mesh,
    face_with_verts,
    calc_edge_median,
    filter_vertical_edges,
    filter_horizontal_edges
    )

def make_stairs(step_count, step_width, bottom_faces, **kwargs):
    """Extrude steps from selected faces

    Args:
        step_count (int): Number of stair steps
        step_width (float): width of each stair step
        bottom_faces (bool): whether to delete bottom faces
        **kwargs: Extra kwargs from StairsProperty
    """
    # Get current edit mesh
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    # Find selected face
    faces = [f for f in bm.faces if f.select]

    for f in faces:
        res = split_quad(bm, f, False, step_count - 1)
        f.select = False
        step_edges = filter_geom(res['geom_inner'], BMEdge)
        step_faces = list({f for e in step_edges for f in e.link_faces})

        if f.normal.x or f.normal.y:
            step_faces.sort(key=lambda f: f.calc_center_median().z, reverse=True)
        else:
            step_faces.sort(key=lambda f: f.calc_center_median().x, reverse=True)

        for idx, fa in enumerate(step_faces):
            # Ref bottom verts - to delete bottom faces
            if fa.normal.z:
                bot_verts = sorted(list(fa.verts), key=lambda v: v.co.y)[:-2]
            else:
                bot_verts = sorted(list(fa.verts), key=lambda v: v.co.z)[:-2]

            # Extrude this step
            ret = bmesh.ops.extrude_discrete_faces(bm, faces=[fa])['faces'][0]
            verts = ret.verts
            bmesh.ops.translate(bm, verts=verts, vec=ret.normal * (step_width * (idx + 1)))

            # Delete bottom Face
            if ret.normal.z:
                verts1 = sorted(list(ret.verts), key=lambda v: v.co.y)[:-2]
            else:
                verts1 = sorted(list(ret.verts), key=lambda v: v.co.z)[:-2]

            if not bottom_faces:
                face = face_with_verts(bm, verts1 + bot_verts)
                bmesh.ops.delete(bm, geom=[face], context=3)
            bmesh.ops.remove_doubles(bm, verts=list(bm.verts))
    bmesh.update_edit_mesh(me, True)


# DEPRECATED
def make_stairs_type1(step_count, step_width, scale, bottom_faces, **kwargs):
    """ Extrude edges to make a sequence of steps """

    # Get current edit mesh
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    # Find all selected faces
    faces = [f for f in bm.faces if f.select]

    def filter_verts(f, vts, lv, rv):
        if f.normal.x:
            verts = sorted([v for v in vts], key=lambda v: v.co.y)
        if f.normal.y:
            verts = sorted([v for v in vts], key=lambda v: v.co.x)
        sp = int(len(verts) / 2)
        lv.extend(verts[:sp])
        rv.extend(verts[sp:])

    for f in faces:
        f.select = False

        # Setup some variables we will use
        vedges = filter_vertical_edges(f.edges, f.normal)
        hedges = filter_horizontal_edges(f.edges, f.normal)

        top = sorted(hedges, key=lambda e: calc_edge_median(e).z)[-1]
        length = vedges[0].calc_length()
        split_length = length / step_count

        left_verts = []
        right_verts = []
        filter_verts(f, f.verts, left_verts, right_verts)

        for i in range(step_count):

            # -- Make Steps
            # Horizontal extrude
            res = bmesh.ops.extrude_edge_only(bm, edges=[top])
            hverts = filter_geom(res['geom'], BMVert)
            edge = filter_geom(res['geom'], BMEdge)[-1]
            bmesh.ops.translate(bm, vec=f.normal * step_width, verts=hverts)

            filter_verts(f, hverts, left_verts, right_verts)
            filter_verts(f, list(top.verts), left_verts, right_verts)

            # Vertical extrude
            res = bmesh.ops.extrude_edge_only(bm, edges=[edge])
            vverts = filter_geom(res['geom'], BMVert)
            top = filter_geom(res['geom'], BMEdge)[-1]
            bmesh.ops.translate(bm, vec=Vector((0, 0, -1)) * split_length, verts=vverts)

            # -- Fill the ends
            for idx, dverts in [(-1, right_verts), (0, left_verts)]:
                # Create new vertex at the bottom of each step
                v = vverts[idx]
                rvert = bmesh.ops.create_vert(bm,
                    co=Vector((v.co.x, v.co.y, v.co.z - (step_count - (i + 1)) * split_length)))['vert']
                cverts = list(set(rvert + dverts))

                # Fill a face
                bmesh.ops.contextual_create(bm, geom=cverts)

                # Update vertices for contextual fill
                if idx == -1:
                    right_verts = []
                    right_verts.extend(rvert)
                if idx == 0:
                    left_verts = []
                    left_verts.extend(rvert)

                    # Remove back face
        bmesh.ops.delete(bm, geom=[f], context=3)

    # Cleanup and editmesh update
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts))
    bmesh.update_edit_mesh(me, True)

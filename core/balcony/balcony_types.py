import bmesh
from bmesh.types import BMVert, BMFace

from ..rails import rails_types as rails
from ...utils import (
    split,
    filter_geom,
    get_edit_mesh,
    face_with_verts,
    )


def make_balcony(width, railing, pw, ph, pd, rw, rh, rd, ww, wh, cpw, cph, hcp, df, fill, amount, off, has_split, **kwargs):
    """ Extrudes selected faces outwards and adds railings to outer edges """

    # Get current edit mesh
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    # Find selected face
    faces = [f for f in bm.faces if f.select]
    if not faces:
        return

    for f in faces:
        # Split the faces
        if has_split:
            f = split(bm, f, amount.y, amount.x, off.x, off.y, off.z)

        # Extrude
        f.select = False
        ret = bmesh.ops.extrude_face_region(bm, geom=[f])
        verts = filter_geom(ret['geom'], BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=-f.normal * width)

        if railing:
            face = filter_geom(ret['geom'], BMFace)[0]
            top_verts1 = list(face.verts)
            top_verts1.sort(key=lambda v: v.co.z)
            top_verts2 = list(f.verts)
            top_verts2.sort(key=lambda v: v.co.z)

            top_face = face_with_verts(bm, top_verts1[2:] + top_verts2[2:])
            reject = bm.edges.get(top_verts2[2:])

            edges = set(list(top_face.edges)).difference([reject])
            rails.make_railing(bm, edges, pw, ph, pd, rw, rh, rd, ww, wh, cpw, cph, hcp, df, fill)

        bmesh.ops.delete(bm, geom=[f], context=3)
    bmesh.update_edit_mesh(me, True)


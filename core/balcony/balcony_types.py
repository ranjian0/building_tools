import bmesh
from bmesh.types import BMVert, BMFace

from ...utils import (
    split,
    filter_geom,
    get_edit_mesh,
    face_with_verts,
)
from ..util_rail import rails_types as rails



def make_balcony(width, railing, pw, ph, pd, rw, rh, rd, ww, wh, cpw, cph, hcp, df, fill, size, off, **kwargs):
    """ Extrudes selected faces outwards and adds railings to outer edges """
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    faces = (face for face in bm.faces if face.select)
    for f in faces:
        f   = split(bm, f, size.y, size.x, off.x, off.y, off.z)
        ret = bmesh.ops.extrude_face_region(bm, geom=[f])
        bmesh.ops.translate(bm,
            verts   = filter_geom(ret['geom'], BMVert),
            vec     = -f.normal * width)

        if railing:
            face        = filter_geom(ret['geom'], bmesh.types.BMFace)[-1]
            top_verts   = sorted(list(face.verts), key=lambda v:v.co.z)[2:]
            edges       = list({e for v in top_verts for e in v.link_edges
                            if e not in list(face.edges)})
            edges.append(bm.edges.get(top_verts))
            rails.make_railing(bm, edges, pw, ph, pd, rw, rh, rd, ww, wh, cpw, cph, hcp, df, fill)

        bmesh.ops.delete(bm, geom=[f], context=3)

    bmesh.update_edit_mesh(me, True)


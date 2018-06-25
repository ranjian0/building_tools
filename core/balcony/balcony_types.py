import bmesh
from bmesh.types import BMVert, BMFace

from ..rails import MakeRailing
from ...utils import (
    split,
    filter_geom,
    get_edit_mesh,
    calc_edge_median,
    )


def make_balcony(bm, faces, width, railing, size, off, open_side, **kwargs):
    """Generate balcony geometry

    Args:
        *args: see balcony_props.py for types and description
        **kwargs: extra kwargs from BalconyProperty
    """

    for f in faces:
        f   = split(bm, f, size.y, size.x, off.x, off.y, off.z)
        ret = bmesh.ops.extrude_face_region(bm, geom=[f])
        bmesh.ops.translate(bm,
            verts=filter_geom(ret['geom'], BMVert),
            vec=-f.normal * width)

        if railing:
            face      = filter_geom(ret['geom'], bmesh.types.BMFace)[-1]
            top_verts = sorted(list(face.verts), key=lambda v:v.co.z)[2:]
            edges     = list({e for v in top_verts for e in v.link_edges
                            if e not in list(face.edges)})

            if f.normal.y:
                edges.sort(key=lambda e:calc_edge_median(e).x, reverse=f.normal.y < 0)
            elif f.normal.x:
                edges.sort(key=lambda e:calc_edge_median(e).y, reverse=f.normal.x > 0)
            left, right = edges

            front = bm.edges.get(top_verts)

            r_edges = []
            if open_side == 'NONE':
                r_edges = [left, right, front]
            elif open_side == 'FRONT':
                r_edges = [left, right]
            elif open_side == 'LEFT':
                r_edges = [front, right]
            elif open_side == 'RIGHT':
                r_edges = [front, left]

            MakeRailing().from_edges(bm, r_edges, **kwargs)

        bmesh.ops.delete(bm, geom=[f], context=3)

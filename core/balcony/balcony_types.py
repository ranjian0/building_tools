import bmesh
from bmesh.types import BMVert, BMFace

from ..rails import create_railing_from_edges
from ...utils import (
    FaceMap,
    filter_geom,
    calc_edge_median,
    add_faces_to_map,
    move_slab_splitface_to_wall,
    inset_face_with_scale_offset,
)


def create_balcony(bm, faces, prop):
    """Generate balcony geometry
    """
    for f in faces:
        size, off = prop.size_offset.size, prop.size_offset.offset
        f = inset_face_with_scale_offset(bm, f, size.y, size.x, off.x, off.y, off.z)
        f = move_slab_splitface_to_wall(bm, f)

        add_faces_to_map(bm, [f], FaceMap.BALCONY)
        ret = bmesh.ops.extrude_face_region(bm, geom=[f])

        map_balcony_faces(bm, ret)
        bmesh.ops.translate(
            bm, verts=filter_geom(ret["geom"], BMVert), vec=-f.normal * prop.width
        )

        if prop.railing:
            add_railing_to_balcony_edges(bm, ret["geom"], f.normal, prop)
        bmesh.ops.delete(bm, geom=[f], context="FACES_ONLY")


def add_railing_to_balcony_edges(bm, balcony_geom, balcony_normal, prop):
    """Add railing to the balcony
    """
    face = filter_geom(balcony_geom, BMFace).pop()
    top_verts = sorted(face.verts, key=lambda v: v.co.z)[2:]
    edges = list(
        {e for v in top_verts for e in v.link_edges if e not in list(face.edges)}
    )
    sort_edges_from_normal_direction(edges, balcony_normal)

    left, right = edges
    front = bm.edges.get(top_verts)
    r_edges = choose_edges_from_direction(prop.open_side, front, left, right)
    create_railing_from_edges(bm, r_edges, prop.rail)


def sort_edges_from_normal_direction(edges, normal):
    """sort edges based on normal direction
    """
    if normal.y:
        edges.sort(key=lambda e: calc_edge_median(e).x, reverse=normal.y < 0)
    elif normal.x:
        edges.sort(key=lambda e: calc_edge_median(e).y, reverse=normal.x > 0)


def choose_edges_from_direction(direction, front, left, right):
    """filter out the edge specified by direction
    """
    return {
        "LEFT": [front, right],
        "FRONT": [left, right],
        "RIGHT": [front, left],
        "NONE": [left, right, front],
    }.get(direction)


def map_balcony_faces(bm, geom):
    """ Add balcony faces to their facemap """
    new_faces = {
        face
        for f in filter_geom(geom["geom"], BMFace)
        for e in f.edges
        for face in e.link_faces
    }
    add_faces_to_map(bm, new_faces, FaceMap.BALCONY)

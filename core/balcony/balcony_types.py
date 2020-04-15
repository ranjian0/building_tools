import bmesh
from mathutils import Vector
from bmesh.types import BMVert, BMFace

from ...utils import (
    FaceMap,
    filter_geom,
    local_to_global,
    add_faces_to_map,
    calc_face_dimensions,
    inset_face_with_scale_offset,
    get_top_faces,
    sort_edges,
)

from ..railing.railing import create_railing


def create_balcony(bm, faces, prop):
    """Generate balcony geometry
    """
    for f in faces:
        normal = f.normal.copy()
        f = create_balcony_split(bm, f, prop.size_offset)
        add_faces_to_map(bm, [f], FaceMap.BALCONY)

        front, top = extrude_balcony(bm, f, prop.width, normal)

        if prop.has_railing:
            add_railing_to_balcony(bm, top, normal, prop)
        bmesh.ops.delete(bm, geom=[f], context="FACES_ONLY")


def extrude_balcony(bm, face, depth, normal):
    front = filter_geom(bmesh.ops.extrude_face_region(bm, geom=[face])["geom"], BMFace)[0]
    map_balcony_faces(bm, front)
    bmesh.ops.translate(
        bm, verts=front.verts, vec=normal * depth
    )
    
    top = get_top_faces(f for e in front.edges for f in e.link_faces)[0]
    return front, top


def add_railing_to_balcony(bm, top, balcony_normal, prop):
    """Add railing to the balcony
    """
    ret = bmesh.ops.duplicate(bm, geom=[top])
    dup_top = filter_geom(ret["geom"], BMFace)[0]

    ret = bmesh.ops.inset_individual(
        bm, faces=[dup_top], thickness=prop.rail.offset, use_even_offset=True
    )
    bmesh.ops.delete(bm, geom=ret["faces"], context="FACES")

    edges = sort_edges(dup_top.edges, balcony_normal)[1:]
    railing_geom = bmesh.ops.extrude_edge_only(bm, edges=edges)["geom"]
    bmesh.ops.translate(
        bm, verts=filter_geom(railing_geom, BMVert), vec=(0., 0., prop.rail.corner_post_height)
    )

    bmesh.ops.delete(bm, geom=[dup_top], context="FACES")

    railing_faces = filter_geom(railing_geom, BMFace)
    create_railing(bm, railing_faces, prop.rail, balcony_normal)


def map_balcony_faces(bm, face):
    """ Add balcony faces to their facemap """
    new_faces = {
        f
        for e in face.edges
        for f in e.link_faces
    }
    add_faces_to_map(bm, new_faces, FaceMap.BALCONY)


def create_balcony_split(bm, face, prop):
    """Use properties from SplitOffset to subdivide face into regular quads
    """
    wall_w, wall_h = calc_face_dimensions(face)
    scale_x = prop.size.x/wall_w
    scale_y = prop.size.y/wall_h
    offset = local_to_global(face, Vector((prop.offset.x, prop.offset.y, 0.0)))
    return inset_face_with_scale_offset(bm, face, scale_y, scale_x, offset.x, offset.y, offset.z)

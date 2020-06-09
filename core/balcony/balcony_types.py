import bmesh
from bmesh.types import BMVert, BMFace
from mathutils import Vector

from ...utils import (
    clamp,
    FaceMap,
    local_xyz,
    sort_edges,
    valid_ngon,
    filter_geom,
    create_face,
    get_top_faces,
    popup_message,
    add_faces_to_map,
    calc_face_dimensions,
)

from ..railing.railing import create_railing


def create_balcony(bm, faces, prop):
    """Generate balcony geometry
    """
    for f in faces:
        if not valid_ngon(f):
            popup_message("Balcony creation not supported for non-rectangular n-gon!", "Ngon Error")
            return False

        f.select = False

        normal = f.normal.copy()
        f = create_balcony_split(bm, f, prop)
        add_faces_to_map(bm, [f], FaceMap.BALCONY)

        front, top = extrude_balcony(bm, f, prop.size_offset.size.y, normal)

        if prop.has_railing:
            add_railing_to_balcony(bm, top, normal, prop)
        bmesh.ops.delete(bm, geom=[f], context="FACES_ONLY")


def extrude_balcony(bm, face, depth, normal):
    front = filter_geom(bmesh.ops.extrude_face_region(bm, geom=[face])["geom"], BMFace)[0]
    map_balcony_faces(bm, front)
    bmesh.ops.translate(bm, verts=front.verts, vec=normal * depth)

    top = get_top_faces(f for e in front.edges for f in e.link_faces)[0]
    return front, top


def add_railing_to_balcony(bm, top, balcony_normal, prop):
    """Add railing to the balcony
    """
    ret = bmesh.ops.duplicate(bm, geom=[top])
    dup_top = filter_geom(ret["geom"], BMFace)[0]

    max_offset = min([*calc_face_dimensions(dup_top)]) / 2
    prop.rail.offset = clamp(prop.rail.offset, 0.0, max_offset - 0.001)
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
    new_faces = {f for e in face.edges for f in e.link_faces}
    add_faces_to_map(bm, new_faces, FaceMap.BALCONY)


def create_balcony_split(bm, face, prop):
    """Use properties to create face
    """
    xyz = local_xyz(face)
    width = min(calc_face_dimensions(face)[0], prop.size_offset.size.x)
    size = Vector((width, prop.slab_height))
    f = create_face(bm, size, prop.size_offset.offset, xyz)
    bmesh.ops.translate(
        bm, verts=f.verts, vec=face.calc_center_bounds() - face.normal*prop.depth_offset
    )
    return f

import bmesh
from bmesh.types import BMVert, BMFace

from ..rails import CreateRailing
from ...utils import split, filter_geom, calc_edge_median


def create_balcony(bm, faces, prop):
    """Generate balcony geometry

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        faces (bmesh.types.BMFace): current selected faces
        prop (bpy.types.PropertyGroup): BalconyProperty
    """

    for f in faces:
        size, off = prop.size_offset.size, prop.size_offset.offset
        f = split(bm, f, size.y, size.x, off.x, off.y, off.z)

        ret = bmesh.ops.extrude_face_region(bm, geom=[f])
        bmesh.ops.translate(
            bm, verts=filter_geom(ret["geom"], BMVert), vec=-f.normal * prop.width
        )

        if prop.railing:
            add_railing_to_balcony_edges(bm, ret["geom"], f.normal, prop)

        bmesh.ops.delete(bm, geom=[f], context="FACES_ONLY")


def add_railing_to_balcony_edges(bm, balcony_geom, balcony_normal, prop):
    """Add railing to the balcony

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        balcony_geom (list): list of geometry from balcony extrusion
        balcony_normal (Vector): normal of face that balcony was created from
        prop (bpy.types.PropertyGroup): BalconyProperty
    """
    face = filter_geom(balcony_geom, BMFace)[-1]
    top_verts = sorted(list(face.verts), key=lambda v: v.co.z)[2:]
    edges = list(
        {e for v in top_verts for e in v.link_edges if e not in list(face.edges)}
    )
    sort_edges_from_normal_direction(edges, balcony_normal)

    left, right = edges
    front = bm.edges.get(top_verts)
    r_edges = choose_edges_from_direction(prop.open_side, front, left, right)

    CreateRailing().from_edges(bm, r_edges, prop.rail)


def sort_edges_from_normal_direction(edges, normal):
    """sort edges based on normal direction

    Args:
        edges (list): edges to sort
        normal (vector): normal direction
    """
    if normal.y:
        edges.sort(key=lambda e: calc_edge_median(e).x, reverse=normal.y < 0)
    elif normal.x:
        edges.sort(key=lambda e: calc_edge_median(e).y, reverse=normal.x > 0)


def choose_edges_from_direction(direction, front, left, right):
    """filter out the edge specified by direction

    Args:
        direction (str): string direction of the edge to remove
        front (bmesh.types.BMEdge): front edge of balcony
        left (bmesh.types.BMEdge): left edge of balcony
        right (bmesh.types.BMEdge): right edge of balcony

    Returns:
        list(bmesh.types.BMEdge): edges that aro not in specified direction
    """
    r_edges = []
    if direction == "NONE":
        r_edges = [left, right, front]
    elif direction == "FRONT":
        r_edges = [left, right]
    elif direction == "LEFT":
        r_edges = [front, right]
    elif direction == "RIGHT":
        r_edges = [front, left]
    return r_edges

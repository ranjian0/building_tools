import bpy
import math
import bmesh
import operator
import functools as ft
from mathutils import Matrix
from bmesh.types import BMVert


def get_edit_mesh():
    """ Get editmode mesh
    """
    return bpy.context.edit_object.data


def create_mesh(name):
    """ Make new mesh data
    """
    return bpy.data.meshes.new(name)


def select(elements, val=True):
    """ For each item in elements set select to val
    """
    for el in elements:
        el.select_set(val)


def validate(elements):
    """ Return only valid items in elements
    """
    return list(filter(lambda el: el.is_valid, elements))


def filter_geom(geom, _type):
    """ Find all elements of type _type in geom iterable
    """
    return list(filter(lambda x: isinstance(x, _type), geom))


def sort_edges_clockwise(edges):
    """ sort edges clockwise based on angle from their median center
    """
    median_reference = ft.reduce(operator.add, map(calc_edge_median, edges)) / len(
        edges
    )

    def sort_function(edge):
        vector_difference = median_reference - calc_edge_median(edge)
        return math.atan2(vector_difference.y, vector_difference.x)

    return sorted(edges, key=sort_function, reverse=True)


def filter_vertical_edges(edges, normal):
    """ Determine edges that are vertical based on a normal value
    """
    res = []
    rnd = ft.partial(round, ndigits=3)

    for e in edges:
        if normal.x:
            s = set([rnd(v.co.y) for v in e.verts])
        else:
            s = set([rnd(v.co.x) for v in e.verts])

        if len(s) == 1:
            res.append(e)
    return res


def filter_horizontal_edges(edges, normal):
    """ Determine edges that are horizontal based on a normal value
    """
    res = []
    rnd = ft.partial(round, ndigits=3)

    for e in edges:
        if normal.z:
            s = set([rnd(v.co.y) for v in e.verts])
        else:
            s = set([rnd(v.co.z) for v in e.verts])

        if len(s) == 1:
            res.append(e)
    return res


def calc_edge_median(edge):
    """ Calculate the center position of edge
    """
    return ft.reduce(operator.add, [v.co for v in edge.verts]) / len(edge.verts)


def calc_verts_median(verts):
    """ Determine the median position of verts
    """
    return ft.reduce(operator.add, [v.co for v in verts]) / len(verts)


def calc_face_dimensions(face):
    """ Determine the width and height of face
    """
    vertical = filter_vertical_edges(face.edges, face.normal)[-1]
    horizontal = filter_horizontal_edges(face.edges, face.normal)[-1]
    return horizontal.calc_length(), vertical.calc_length()


def face_with_verts(bm, verts, default=None):
    """ Find a face in the bmesh with the given verts
    """
    for face in bm.faces:
        if len(set(list(face.verts) + verts)) == len(verts):
            return face
    return default


def subdivide_face_edges_vertical(bm, face, cuts=4):
    """ Subdivide the vertical edges of a face
    """
    e = filter_horizontal_edges(face.edges, face.normal)
    return bmesh.ops.subdivide_edges(bm, edges=e, cuts=cuts)


def subdivide_face_edges_horizontal(bm, face, cuts=4):
    """ Subdivide the horizontal edges of a face
    """
    e = filter_vertical_edges(face.edges, face.normal)
    return bmesh.ops.subdivide_edges(bm, edges=e, cuts=cuts)


def inset_face_with_scale_offset(bm, face, scale_y, scale_x, offx=0, offy=0, offz=0):
    """ Inset a face using right angled cuts, then offset and scale inner face
    """
    cuts = 2
    scale = cuts + 1
    scale_y *= scale
    scale_x *= scale

    do_vertical = scale_y < scale
    do_horizontal = scale_x < scale

    if not do_horizontal and not do_vertical:
        return face

    face.select = False
    verts = subdivide_flagged_edges(
        bm, face, do_horizontal, do_vertical, scale_x, scale_y
    )
    offset_flagged_verts(bm, verts, do_horizontal, do_vertical, offx, offy, offz)
    return face_with_verts(bm, verts)


def subdivide_flagged_edges(bm, face, cut_horizontal, cut_vertical, scale_x, scale_y):
    """ Subdivide the edges of a face that are flagged
    """
    normal = face.normal
    median = face.calc_center_median()
    if cut_horizontal:
        horizontal = filter_horizontal_edges(face.edges, normal)
        verts = subdivide_edges_and_scale_inner(
            bm, horizontal, (scale_x, scale_x, 1), median
        )

    if cut_vertical:
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts))
        face = face_with_verts(bm, verts) if cut_horizontal else face
        vertical = filter_vertical_edges(face.edges, normal)
        verts = subdivide_edges_and_scale_inner(bm, vertical, (1, 1, scale_y), median)
    return verts


def offset_flagged_verts(bm, verts, horizontal, vertical, offx, offy, offz):
    """ Move the flagged vertices
    """
    if horizontal and vertical:
        link_edges = [e for v in verts for e in v.link_edges]
        all_verts = list({v for e in link_edges for v in e.verts})
        bmesh.ops.translate(bm, verts=all_verts, vec=(offx, offy, 0))
    elif horizontal and not vertical:
        bmesh.ops.translate(bm, verts=verts, vec=(offx, offy, 0))
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, offz))


def subdivide_edges_and_scale_inner(bm, edges, scale, scale_center):
    """ subdivide the edges twice and scale the middle section
    """
    sp_res = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=2)
    verts = filter_geom(sp_res["geom_inner"], BMVert)
    bmesh.ops.scale(bm, vec=scale, verts=verts, space=Matrix.Translation(-scale_center))
    return verts


def edge_split_offset(bm, edges, verts, offset, connect_verts=False):
    """ Split the edges, offset amount from verts
    """
    new_verts = []
    for idx, e in enumerate(edges):
        vert = verts[idx]
        _, v = bmesh.utils.edge_split(e, vert, offset / e.calc_length())
        new_verts.append(v)

    if connect_verts:
        res = bmesh.ops.connect_verts(bm, verts=new_verts).get("edges")
        return res
    return new_verts


def boundary_edges_from_face_selection(bm):
    """ Find all edges that bound the current selected faces
    """
    selected_faces = [f for f in bm.faces if f.select]
    all_edges = list({e for f in selected_faces for e in f.edges})
    edge_is_boundary = (
        lambda e: len({f for f in e.link_faces if f in selected_faces}) == 1
    )
    return [e for e in all_edges if edge_is_boundary(e)]

import bpy
import math
import bmesh
import operator
import functools as ft
from mathutils import Matrix
from bmesh.types import BMVert


def get_edit_mesh():
    """ Get editmode mesh """
    return bpy.context.edit_object.data


def create_mesh(name):
    """ Make new mesh data """
    return bpy.data.meshes.new(name)


def select(elements, val=True):
    """ For each item in elements set select to val """
    for el in elements:
        el.select_set(val)


def filter_geom(geom, _type):
    """ Find all elements of type _type in geom iterable """
    return list(filter(lambda x: isinstance(x, _type), geom))


def sort_edges_clockwise(edges):
    median_reference = ft.reduce(operator.add, map(calc_edge_median, edges)) / len(
        edges
    )

    def sort_function(edge):
        vector_difference = median_reference - calc_edge_median(edge)
        return math.atan2(vector_difference.y, vector_difference.x)

    return sorted(edges, key=sort_function, reverse=True)


def filter_vertical_edges(edges, normal):
    """ Determine edges that are vertical based on a normal value """
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
    """ Determine edges that are horizontal based on a normal value """
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
    """ Calculate the center position of edge """
    return ft.reduce(operator.add, [v.co for v in edge.verts]) / len(edge.verts)


def calc_verts_median(verts):
    """ Determine the median position of verts """
    return ft.reduce(operator.add, [v.co for v in verts]) / len(verts)


def calc_face_dimensions(face):
    """ Determine the width and height of face """
    vertical = filter_vertical_edges(face.edges, face.normal)[-1]
    horizontal = filter_horizontal_edges(face.edges, face.normal)[-1]
    return horizontal.calc_length(), vertical.calc_length()


def face_with_verts(bm, verts, default=None):
    """ Find a face in the bmesh with the given verts"""
    for face in bm.faces:
        if len(set(list(face.verts) + verts)) == len(verts):
            return face
    return default


def split_quad(bm, face, vertical=False, cuts=4):
    """ Subdivide a quad's edges into even horizontal/vertical cuts """

    res = None
    if vertical:
        e = filter_horizontal_edges(face.edges, face.normal)
        res = bmesh.ops.subdivide_edges(bm, edges=e, cuts=cuts)
    else:
        e = filter_vertical_edges(face.edges, face.normal)
        res = bmesh.ops.subdivide_edges(bm, edges=e, cuts=cuts)
    return res


def split(bm, face, svertical, shorizontal, offx=0, offy=0, offz=0):
    """ Split a quad into regular quad sections (basically an inset with only right-angled edges) """

    # scale svertical and shorizontal
    scale = 3  # number of cuts + 1
    svertical *= scale
    shorizontal *= scale

    do_vertical = svertical < scale
    do_horizontal = shorizontal < scale

    face.select = False
    median = face.calc_center_median()

    # SKIP BOTH
    # `````````
    if not do_horizontal and not do_vertical:
        return face

    if do_horizontal:
        # Determine horizontal edges
        # --  edges whose verts have similar z coord
        horizontal = list(
            filter(
                lambda e: len(set([round(v.co.z, 1) for v in e.verts])) == 1, face.edges
            )
        )

        # Subdivide edges
        sp_res = bmesh.ops.subdivide_edges(bm, edges=horizontal, cuts=2)
        verts = filter_geom(sp_res["geom_inner"], BMVert)

        # Scale subdivide face
        T = Matrix.Translation(-median)
        bmesh.ops.scale(bm, vec=(shorizontal, shorizontal, 1), verts=verts, space=T)

    if do_vertical:
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts))
        face = face_with_verts(bm, verts) if do_horizontal else face

        # Determine vertical edges
        # -- edges whose verts have similar x/y coord
        other = list(
            filter(
                lambda e: len(set([round(v.co.z, 1) for v in e.verts])) == 1, face.edges
            )
        )
        vertical = list(set(face.edges) - set(other))

        # Subdivide
        sp_res = bmesh.ops.subdivide_edges(bm, edges=vertical, cuts=2)
        verts = filter_geom(sp_res["geom_inner"], BMVert)

        # Scale subdivide face
        T = Matrix.Translation(-median)
        bmesh.ops.scale(bm, vec=(1, 1, svertical), verts=verts, space=T)

    # OFFSET VERTS
    # ---------------------
    # -- horizontal offset
    if do_horizontal and do_vertical:
        link_edges = [e for v in verts for e in v.link_edges]
        all_verts = list({v for e in link_edges for v in e.verts})
        bmesh.ops.translate(bm, verts=all_verts, vec=(offx, offy, 0))
    elif do_horizontal and not do_vertical:
        bmesh.ops.translate(bm, verts=verts, vec=(offx, offy, 0))

    # -- vertical offset
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, offz))

    face = face_with_verts(bm, verts)
    return face


def edge_split_offset(bm, edges, verts, offset, connect_verts=False):
    """ Split the edges, offset amount from verts """

    new_verts = []
    for idx, e in enumerate(edges):
        vert = verts[idx]
        _, v = bmesh.utils.edge_split(e, vert, offset / e.calc_length())
        new_verts.append(v)

    if connect_verts:
        res = bmesh.ops.connect_verts(bm, verts=new_verts).get("edges")
        return res
    return new_verts

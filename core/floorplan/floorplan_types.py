import bmesh
from bmesh.types import BMVert
from mathutils import Vector, Matrix

import random
from ...utils import (
    clamp,
    plane,
    circle,
    filter_geom,
    calc_edge_median,
    filter_vertical_edges,
    filter_horizontal_edges,
)


def fp_rectangular(bm, width, length, **kwargs):
    """Create plane in provided bmesh

    Args:
        bm     (bmesh.types.BMesh): bmesh to create plane in
        width  (float): width of plane
        length (float): length of plane
    """
    plane(bm, width, length)


def fp_circular(bm, radius, segs, cap_tris, **kwargs):
    """Create circle in provided bmesh

    Args:
        bm       (bmesh.types.BMESH): bmesh to create cirlce in
        radius   (float): radius of circle
        segs     (int): number of segments for circle
        cap_tris (bool): whether to fill the circle with triangles
    """
    circle(bm, radius, segs, cap_tris)


def fp_composite(bm, width, length, tl1, tl2, tl3, tl4, **kwargs):
    """Create a fan shape from rectangle
        .____.
        |    |
        |    |
    .___......___.
    |   .    .   |
    |   .    .   |
    .___......___.
        |    |
        |    |
        .____.

    Args:
        bm     (bmesh.types.BMesh): bmesh to create shape in
        width  (float): width of inner rectangle
        length (float): length of inner rectangle
        tl1 (float): length of fan (bottom)
        tl2 (float): length of fan (left)
        tl3 (float): length of fan (right)
        tl4 (float): length of fan (top)
    """

    base = plane(bm, width, length)
    ref = list(bm.faces)[-1].calc_center_median()

    # Sort edges to make predictable winding
    edges = list(bm.edges)
    edges.sort(key=lambda ed: calc_edge_median(ed).x)
    edges.sort(key=lambda ed: calc_edge_median(ed).y)

    exts = [tl1, tl2, tl3, tl4]
    for idx, e in enumerate(edges):
        if exts[idx] > 0:
            res = bmesh.ops.extrude_edge_only(bm, edges=[e])
            verts = filter_geom(res["geom"], BMVert)

            v = calc_edge_median(e) - ref
            v.normalize()
            bmesh.ops.translate(bm, verts=verts, vec=v * exts[idx])


def fp_hshaped(bm, width, length, tl1, tl2, tl3, tl4, tw1, tw2, tw3, tw4, **kwargs):
    """Create H_shaped geometry from a rectangle

    .___.      .___.
    |   |      |   |
    |   |      |   |
    |   .______.
    |   .      .   |
    |   .______.   |
    |   |      |   |
    |   |      |   |
    .___.      .___.

    Args:
        bm     (bmesh.types.BMesh): bmesh to create shape in
        width  (float): width of inner rectangle
        length (float): length of inner rectangle
        tl1 (float): length of fan (bottom-left)
        tl2 (float): length of fan (bottom-right)
        tl3 (float): length of fan (top-left)
        tl4 (float): length of fan (top-right)
        tw1 (float): width of fan (bottom-left)
        tw2 (float): width of fan (bottom-right)
        tw3 (float): width of fan (top-left)
        tw4 (float): width of fan (top-right)
    """

    base = plane(bm, width, length)
    face = list(bm.faces)[-1]
    ref = face.calc_center_median()
    n = face.normal

    # make side extrusions
    for e in filter_vertical_edges(bm.edges, n):
        res = bmesh.ops.extrude_edge_only(bm, edges=[e])
        verts = filter_geom(res["geom"], BMVert)

        v = calc_edge_median(e) - ref
        v.normalize()

        bmesh.ops.translate(bm, verts=verts, vec=v)

    # Find all top edges and filter ones in the middle
    op_edges = filter_horizontal_edges(bm.edges, n)
    # --filter mid row
    op_edges.sort(key=lambda ed: calc_edge_median(ed).x)
    op_edges = op_edges[:2] + op_edges[4:]
    # -- make deterministic
    op_edges.sort(key=lambda ed: calc_edge_median(ed).y)
    lext = [tl1, tl2, tl3, tl4]
    wext = [tw1, tw2, tw3, tw4]

    for idx, e in enumerate(op_edges):

        if lext[idx] > 0:
            res = bmesh.ops.extrude_edge_only(bm, edges=[e])
            verts = filter_geom(res["geom"], BMVert)

            v = calc_edge_median(e) - ref
            v.normalize()

            flt_func = min if v.x > 0 else max
            mv1 = flt_func(list(e.verts), key=lambda v: v.co.x)
            mv2 = flt_func(verts, key=lambda v: v.co.x)

            bmesh.ops.translate(bm, verts=verts, vec=Vector((0, v.y, 0)) * lext[idx])
            bmesh.ops.translate(
                bm, verts=[mv1, mv2], vec=Vector((-v.x, 0, 0)) * wext[idx]
            )


def fp_random(bm, seed, width, length, **kwargs):
    """ Create randomly generated building footprint/floorplan

    Args:
        bm     (bmesh.types.BMesh): bmesh to create plane in
        seed   (int): random seed
        width  (float): width of base plane
        length (float): length of base plane

    """
    random.seed(seed)
    sc_x = Matrix.Scale(width, 4, (1, 0, 0))
    sc_y = Matrix.Scale(length, 4, (0, 1, 0))
    mat = sc_x @ sc_y
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1, matrix=mat)

    sample = random.sample(list(bm.edges), random.randrange(1, len(bm.edges)))
    ref = list(bm.faces)[-1].calc_center_median()
    for edge in sample:
        # -- get edge center and length
        edge_median = calc_edge_median(edge)
        edge_length = edge.calc_length()

        # -- subdivide
        res = bmesh.ops.subdivide_edges(bm, edges=[edge], cuts=2)
        new_verts = filter_geom(res["geom_inner"], BMVert)
        new_edge = list(set(new_verts[0].link_edges) & set(new_verts[1].link_edges))[-1]

        # -- resize new edge
        axis = (
            Vector((1, 0, 0))
            if new_verts[0].co.y == new_verts[1].co.y
            else Vector((0, 1, 0))
        )
        scale_factor = clamp(
            random.random() * edge_length / new_edge.calc_length(), 1, 2.95
        )
        bmesh.ops.scale(
            bm,
            verts=new_verts,
            vec=axis * scale_factor,
            space=Matrix.Translation(-edge_median),
        )

        # -- offset
        if random.choice([0, 1]):
            max_offset = (edge_length - new_edge.calc_length()) / 2
            rand_offset = random.random() * max_offset
            bmesh.ops.translate(bm, verts=new_verts, vec=axis * rand_offset)

        # --extrude
        res = bmesh.ops.extrude_edge_only(bm, edges=[new_edge])
        bmesh.ops.translate(
            bm,
            verts=filter_geom(res["geom"], BMVert),
            vec=(edge_median - ref).normalized()
            * random.randrange(1, int(edge_length / 2)),
        )

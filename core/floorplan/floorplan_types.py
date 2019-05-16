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
    sort_edges_clockwise,
    filter_vertical_edges,
    filter_horizontal_edges,
)


def create_rectangular_floorplan(bm, prop):
    """Create plane in provided bmesh

    Args:
        bm (bmesh.types.BMesh): bmesh to create plane in
        prop (bpy.types.PropertyGroup): FloorplanPropertyGroup
    """
    plane(bm, prop.width, prop.length)


def create_circular_floorplan(bm, prop):
    """Create circle in provided bmesh

    Args:
        bm (bmesh.types.BMesh): bmesh to create circle in
        prop (bpy.types.PropertyGroup): FloorplanPropertyGroup
    """
    circle(bm, prop.radius, prop.segments, prop.cap_tris)


def create_composite_floorplan(bm, prop):
    """Create a fan shape from a rectangle
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
        bm (bmesh.types.BMesh): bmesh to create shape in
        prop (bpy.types.PropertyGroup): FloorplanPropertyGroup
    """

    base = plane(bm, prop.width, prop.length)
    median_reference = list(bm.faces)[-1].calc_center_median()

    # Sort edges to make predictable winding
    edges = sort_edges_clockwise(bm.edges)

    exts = [prop.tl1, prop.tl2, prop.tl3, prop.tl4]
    for idx, e in enumerate(edges):
        if exts[idx] > 0:
            res = bmesh.ops.extrude_edge_only(bm, edges=[e])
            verts = filter_geom(res["geom"], BMVert)

            v = calc_edge_median(e) - median_reference
            v.normalize()
            bmesh.ops.translate(bm, verts=verts, vec=v * exts[idx])


def create_hshaped_floorplan(bm, prop):
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
        bm (bmesh.types.BMesh): bmesh to create shape in
        prop (bpy.types.PropertyGroup): FloorplanPropertyGroup
    """

    base = plane(bm, prop.width, prop.length)
    face = list(bm.faces)[-1]
    normal = face.normal
    median_reference = face.calc_center_median()

    # make side extrusions
    for edge in filter_vertical_edges(bm.edges, normal):
        res = bmesh.ops.extrude_edge_only(bm, edges=[edge])
        verts = filter_geom(res["geom"], BMVert)

        v = calc_edge_median(edge) - median_reference
        v.normalize()

        bmesh.ops.translate(bm, verts=verts, vec=v)

    # Find all top edges and remove ones in the middle
    op_edges = filter_horizontal_edges(bm.edges, normal)

    # --remove mid row
    op_edges.sort(key=lambda ed: calc_edge_median(ed).x)
    op_edges = op_edges[:2] + op_edges[4:]

    # -- make deterministic
    op_edges = sort_edges_clockwise(op_edges)
    lext = [prop.tl1, prop.tl2, prop.tl3, prop.tl4]
    wext = [prop.tw1, prop.tw2, prop.tw3, prop.tw4]

    for idx, edge in enumerate(op_edges):

        if lext[idx] > 0:
            res = bmesh.ops.extrude_edge_only(bm, edges=[edge])
            verts = filter_geom(res["geom"], BMVert)

            v = calc_edge_median(edge) - median_reference
            v.normalize()

            filter_function = min if v.x > 0 else max
            mv1 = filter_function(list(edge.verts), key=lambda v: v.co.x)
            mv2 = filter_function(verts, key=lambda v: v.co.x)

            bmesh.ops.translate(bm, verts=verts, vec=Vector((0, v.y, 0)) * lext[idx])
            bmesh.ops.translate(
                bm, verts=[mv1, mv2], vec=Vector((-v.x, 0, 0)) * wext[idx]
            )


def create_random_floorplan(bm, prop):
    """ Create randomly generated building footprint/floorplan

    Args:
        bm (bmesh.types.BMesh): bmesh to create plane in
        prop (bpy.types.PropertyGroup): FloorplanPropertyGroup
    """
    random.seed(prop.seed)
    sc_x = Matrix.Scale(prop.width, 4, (1, 0, 0))
    sc_y = Matrix.Scale(prop.length, 4, (0, 1, 0))
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

        try:
            extrude_length = random.randrange(1, int(edge_length / 2))
        except ValueError:
            extrude_length = 1

        bmesh.ops.translate(
            bm,
            verts=filter_geom(res["geom"], BMVert),
            vec=(edge_median - ref).normalized() * extrude_length,
        )

import math
import random

import bmesh
from bmesh.types import BMVert
from mathutils import Vector, Matrix

from ...utils import (
    clamp,
    plane,
    circle,
    VEC_RIGHT,
    VEC_FORWARD,
    filter_geom,
    calc_edge_median,
    sort_edges_clockwise,
    filter_vertical_edges,
    filter_horizontal_edges,
)


def create_rectangular_floorplan(bm, prop):
    """Create plane in provided bmesh
    """
    plane(bm, prop.width / 2, prop.length / 2)


def create_circular_floorplan(bm, prop):
    """Create circle in provided bmesh
    """
    circle(bm, prop.radius, prop.segments)


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

    """
    plane(bm, prop.width / 2, prop.length / 2)
    median_reference = list(bm.faces).pop().calc_center_median()

    edges = sort_edges_clockwise(bm.edges)
    extrusion_lengths = [prop.tl1, prop.tl2, prop.tl3, prop.tl4]
    for idx, e in enumerate(edges):
        if extrusion_lengths[idx] > 0.0:
            res = bmesh.ops.extrude_edge_only(bm, edges=[e])
            verts = filter_geom(res["geom"], BMVert)

            direction = (calc_edge_median(e) - median_reference).normalized()
            bmesh.ops.translate(bm, verts=verts, vec=direction * extrusion_lengths[idx])


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

    """
    plane(bm, prop.width / 2, prop.length / 2)
    face = list(bm.faces).pop()
    median_reference = face.calc_center_median()

    extrude_left_and_right_edges(bm, median_reference)
    extreme_edges = determine_clockwise_extreme_edges_for_extrusion(bm)

    extrusion_lengths = [prop.tl1, prop.tl2, prop.tl3, prop.tl4]
    extrusion_widths = [prop.tw1, prop.tw2, prop.tw3, prop.tw4]
    for idx, edge in enumerate(extreme_edges):
        length, width = extrusion_lengths[idx], extrusion_widths[idx]

        if length > 0.0:
            res = bmesh.ops.extrude_edge_only(bm, edges=[edge])
            verts = filter_geom(res["geom"], BMVert)
            v = (calc_edge_median(edge) - median_reference).normalized()
            bmesh.ops.translate(
                bm, verts=verts, vec=Vector((0, math.copysign(1.0, v.y), 0)) * length
            )

            filter_function = min if v.x > 0 else max
            mv1 = filter_function(list(edge.verts), key=lambda v: v.co.x)
            mv2 = filter_function(verts, key=lambda v: v.co.x)
            bmesh.ops.translate(
                bm, verts=[mv1, mv2],
                # -- subtract 1.0 from the width to offset the default width
                vec=Vector((-math.copysign(1.0, v.x), 0, 0)) * (width - 1.0)
            )


def create_random_floorplan(bm, prop):
    """Create randomly generated building floorplan
    """
    random.seed(prop.seed)
    scale_x = Matrix.Scale(prop.width / 2, 4, (1, 0, 0))
    scale_y = Matrix.Scale(prop.length / 2, 4, (0, 1, 0))
    bmesh.ops.create_grid(
        bm, x_segments=1, y_segments=1, size=1, matrix=scale_x @ scale_y
    )

    amount = prop.extension_amount
    if prop.random_extension_amount:
        amount = random.randrange(len(bm.edges) // 3, len(bm.edges))

    random_edges = random.sample(
        list(bm.edges), amount
    )
    median_reference = list(bm.faces).pop().calc_center_median()
    for edge in random_edges:
        edge_median = calc_edge_median(edge)

        middle_edge = subdivide_edge_twice_and_get_middle(bm, edge)
        random_scale_and_translate(bm, middle_edge)
        random_extrude(bm, middle_edge, (edge_median - median_reference).normalized())


def extrude_left_and_right_edges(bm, median_reference):
    """Extrude the left and right edges of a plane
    """
    for edge in filter_vertical_edges(bm.edges):
        res = bmesh.ops.extrude_edge_only(bm, edges=[edge])
        verts = filter_geom(res["geom"], BMVert)
        bmesh.ops.translate(
            bm,
            verts=verts,
            vec=(calc_edge_median(edge) - median_reference).normalized(),
        )


def determine_clockwise_extreme_edges_for_extrusion(bm):
    """top and bottom extreme edges sorted clockwise
    """
    all_upper_edges = filter_horizontal_edges(bm.edges)
    all_upper_edges.sort(key=lambda ed: calc_edge_median(ed).x)

    upper_extreme_edges = all_upper_edges[:2] + all_upper_edges[4:]
    return sort_edges_clockwise(upper_extreme_edges)


def subdivide_edge_twice_and_get_middle(bm, edge):
    """make two cuts to an edge and return middle edge
    """
    res = bmesh.ops.subdivide_edges(bm, edges=[edge], cuts=2)
    new_verts = filter_geom(res["geom_inner"], BMVert)
    return (set(new_verts[0].link_edges) & set(new_verts[1].link_edges)).pop()


def random_scale_and_translate(bm, middle_edge):
    """scale and translate an edge randomly along its axis
    """
    verts = list(middle_edge.verts)
    length = middle_edge.calc_length()
    median = calc_edge_median(middle_edge)

    axis = VEC_RIGHT if verts[0].co.y == verts[1].co.y else VEC_FORWARD
    scale_factor = clamp(random.random() * 3, 1, 2.95)
    bmesh.ops.scale(
        bm, verts=verts, vec=axis * scale_factor, space=Matrix.Translation(-median)
    )

    if random.choice([0, 1]):
        rand_offset = random.random() * length
        bmesh.ops.translate(bm, verts=verts, vec=axis * rand_offset)


def random_extrude(bm, middle_edge, direction):
    """extrude an edge to a random size to make a plane
    """
    res = bmesh.ops.extrude_edge_only(bm, edges=[middle_edge])
    extrude_length = (random.random() * middle_edge.calc_length()) + 1.0
    bmesh.ops.translate(
        bm, verts=filter_geom(res["geom"], BMVert), vec=direction * extrude_length
    )

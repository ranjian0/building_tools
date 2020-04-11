import bpy
import math
import bmesh
from collections import namedtuple
from mathutils import Vector
from ...utils import (
    FaceMap,
    create_wall,
    edge_tangent,
    map_new_faces,
    add_cube_post,
    array_elements,
    calc_edge_median,
    add_facemap_for_groups,
    align_geometry_to_edge,
    create_cube_without_faces,
)


context = None
RailContext = namedtuple("_RailContext", "normal prop front left right slab_outset")


def create_balcony_railing(bm, edges, prop, normal):
    # -- setup global context
    global context
    active_obj = bpy.context.active_object
    context = RailContext(
        normal, prop, *get_front_left_right_edge(edges, normal),
        active_obj.tracked_properties.slab_outset)

    make_corner_posts(bm, edges)
    make_fill(bm, edges)
    bmesh.ops.remove_doubles(bm, verts=bm.verts)


@map_new_faces(FaceMap.RAILING_POSTS)
def make_corner_posts(bm, edges):
    add_facemap_for_groups(FaceMap.RAILING_POSTS)

    # -- size of corner posts
    rail = context.prop.rail
    width, height = rail.corner_post_width, rail.corner_post_height
    diag_width = math.sqrt(2 * ((width / 2) ** 2))

    front, left, right = get_front_left_right_edge(edges, context.normal)
    for e in edges:
        if e == front:
            continue

        for v in e.verts:
            # -- skip some posts if left/right sides are open
            if vert_is_open(v, front, left, right, context.prop):
                continue

            vtan = [l.calc_tangent() for l in v.link_loops if l.face.normal.z].pop()
            offset = vtan * diag_width

            location = v.co + Vector((0, 0, height / 2)) + offset
            if v not in front.verts:
                # -- make stating posts flush with walls
                location += -context.normal * context.slab_outset

            post = add_cube_post(bm, width, height, location)
            align_geometry_to_edge(bm, post, e)


def make_fill(bm, edges):
    if context.prop.rail.fill == "POSTS":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_RAILS))
        create_fill_posts(bm, edges)
    elif context.prop.rail.fill == "RAILS":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_RAILS))
        create_fill_rails(bm, edges)
    elif context.prop.rail.fill == "WALL":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_WALLS))
        create_fill_walls(bm, edges)


@map_new_faces(FaceMap.RAILING_POSTS, skip=FaceMap.RAILING_RAILS)
def create_fill_posts(bm, edges):
    skip = {context.front: "FRONT", context.left: "LEFT", context.right: "RIGHT"}
    for edge in edges:
        if context.prop.open_side == skip.get(edge):
            continue

        # -- add posts
        add_posts_between_edge(bm, edge)

        # -- add top rail
        rail_pos, rail_size = calc_rail_position_and_size_for_edge(edge)
        rail_pos += Vector((0, 0, context.prop.rail.corner_post_height - context.prop.rail.rail_fill.size / 2))

        rail = map_new_faces(FaceMap.RAILING_RAILS)(create_cube_without_faces)
        rail = rail(bm, rail_size, rail_pos, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)


@map_new_faces(FaceMap.RAILING_RAILS)
def create_fill_rails(bm, edges):
    rail = context.prop.rail
    rail_fill = rail.rail_fill
    skip = {context.front: "FRONT", context.left: "LEFT", context.right: "RIGHT"}
    for edge in edges:
        if context.prop.open_side == skip.get(edge):
            continue

        rail_pos, rail_size = calc_rail_position_and_size_for_edge(edge)
        start, stop = rail_pos, rail_pos + Vector((0, 0, rail.corner_post_height - rail_fill.size/2))

        rail_geom = create_cube_without_faces(bm, rail_size, left=True, right=True)
        align_geometry_to_edge(bm, rail_geom, edge)

        rail_count = int((rail.corner_post_height / rail_fill.size) * rail_fill.density)
        array_elements(bm, rail_geom, rail_count, start, stop, fill_last=True)


@map_new_faces(FaceMap.RAILING_WALLS)
def create_fill_walls(bm, edges):
    rail = context.prop.rail
    wall_fill = rail.wall_fill
    skip = {context.front: "FRONT", context.left: "LEFT", context.right: "RIGHT"}
    for edge in edges:
        if context.prop.open_side == skip.get(edge):
            continue

        v1, v2 = edge.verts
        start, stop = [v.co.copy() for v in edge.verts]
        start += (calc_edge_median(edge) - start).normalized() * rail.corner_post_width
        if v1 not in context.front.verts:
            start += -context.normal * context.slab_outset

        stop += (calc_edge_median(edge) - stop).normalized() * rail.corner_post_width
        if v2 not in context.front.verts:
            stop += -context.normal * context.slab_outset

        wall_pos, wall_size = calc_rail_position_and_size_for_edge(edge)
        wall = create_wall(
            bm, start, stop, rail.corner_post_height, wall_fill.width, edge_tangent(edge)
        )
        wall(delete_faces=["bottom", "left", "right"])


def cross_edge_tangents(edge_a, edge_b):
    return edge_tangent(edge_a).cross(edge_tangent(edge_b))


def get_front_left_right_edge(edges, normal):
    front = [e for e in edges if edge_tangent(e).to_tuple(3) == (-normal).to_tuple(3)].pop()

    other_edges = list(set(edges) - set([front]))
    left, right = sorted(other_edges, key=lambda e : -cross_edge_tangents(e, front).z)
    return front, left, right


def vert_is_open(v, front, left, right, prop):
    """ Determine if this is the vert in an open edge that should not have a post
    """
    if prop.open_side == "LEFT":
        if v in left.verts and v not in front.verts:
            return True
    elif prop.open_side == "RIGHT":
        if v in right.verts and v not in front.verts:
            return True
    return False


def add_posts_between_edge(bm, edge):
    rail = context.prop.rail
    v1, v2 = edge.verts

    # -- create post geometry
    height_v = Vector((0, 0, rail.corner_post_height / 2 - rail.rail_fill.size / 2))
    size = (rail.post_fill.size, rail.post_fill.size, rail.corner_post_height - rail.rail_fill.size)
    post = create_cube_without_faces(bm, size, top=True, bottom=True)
    align_geometry_to_edge(bm, post, edge)

    offset = height_v + (edge_tangent(edge) * rail.corner_post_width/2)
    start, stop = v1.co.copy() + offset, v2.co.copy() + offset

    add_outset = (v1 not in context.front.verts) or (v2 not in context.front.verts)
    if v1 not in context.front.verts:
        start += -context.normal * context.slab_outset
    if v2 not in context.front.verts:
        stop += -context.normal * context.slab_outset

    length = edge.calc_length() + [0, context.slab_outset][add_outset]
    post_count = round((length / rail.post_fill.size) * rail.post_fill.density)
    array_elements(bm, post, post_count, start, stop)


def calc_rail_position_and_size_for_edge(edge):
    v1, v2 = edge.verts
    add_outset = (v1 not in context.front.verts) or (v2 not in context.front.verts)
    rail_len = edge.calc_length() + [0, context.slab_outset][add_outset]
    rail_len -= context.prop.rail.corner_post_width * 2
    rail_size = (rail_len, context.prop.rail.corner_post_width, context.prop.rail.rail_fill.size)

    off = edge_tangent(edge).normalized() * (context.prop.rail.corner_post_width / 2)
    rail_pos = calc_edge_median(edge) + off + [Vector(), -context.normal * context.slab_outset/2][add_outset]
    return rail_pos, rail_size

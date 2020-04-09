import bpy
import math
import bmesh

from mathutils import Vector
from ...utils import (
    edge_tangent,
    add_cube_post,
    align_geometry_to_edge,
    add_posts_between_loops,
    create_cube_without_faces,
    calc_rail_position_and_size_for_loop,
)


def create_balcony_railing(bm, edges, prop, normal):
    make_corner_posts(bm, edges, normal, prop)
    # make_fill(bm, loops, prop)
    bmesh.ops.remove_doubles(bm, verts=bm.verts)


# @map_new_faces(FaceMap.RAILING_POSTS)
def make_corner_posts(bm, edges, normal, prop):
    # add_facemap_for_groups(FaceMap.RAILING_POSTS)
    rail = prop.rail

    front_edge = [e for e in edges if edge_tangent(e).to_tuple(3) == (-normal).to_tuple(3)].pop()
    other_edges = list(set(edges) - set([front_edge]))
    left, right = sorted(other_edges, key=lambda e : -cross_edge_tangents(e, front_edge).z)

    # -- flag to push posts adjacent to walls
    active_obj = bpy.context.active_object
    slab_outset = active_obj.tracked_properties.slab_outset

    width, height = rail.corner_post_width, rail.corner_post_height
    diag_width = math.sqrt(2 * ((width / 2) ** 2))
    for e in edges:
        if e == front_edge:
            continue

        for v in e.verts:
            # -- skip some posts if left/right sides are open
            if vert_is_open(v, front_edge, left, right, prop):
                continue

            vtan = [l.calc_tangent() for l in v.link_loops if l.face.normal.z].pop()
            offset = vtan * diag_width

            location = v.co + Vector((0, 0, height / 2)) + offset
            if v not in front_edge.verts:
                # -- make stating posts flush with walls
                location += -normal * slab_outset

            post = add_cube_post(bm, width, height, location)
            align_geometry_to_edge(bm, post, e)


def make_fill(bm, loops, prop):
    if prop.fill == "POSTS":
        # add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_RAILS))
        create_fill_posts(bm, loops, prop)
    elif prop.fill == "RAILS":
        # add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_RAILS))
        create_fill_rails(bm, loops, prop)
    elif prop.fill == "WALL":
        # add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_WALLS))
        create_fill_walls(bm, loops, prop)


# @map_new_faces(FaceMap.RAILING_RAILS)
def create_fill_posts(bm, loops, prop):
    for loop in loops:
        edge = loop.edge

        # -- add posts
        add_posts_between_loops(bm, [loop, loop.link_loop_next], prop)
        # fill_post_for_colinear_gap(bm, edge, prop, raildata)

        # -- add top rail
        rail_pos, rail_size = calc_rail_position_and_size_for_loop(loop, prop)
        rail_pos += Vector((0, 0, prop.corner_post_height - prop.rail_fill.size / 2))

        # rail = map_new_faces(FaceMap.RAILING_RAILS)(create_cube_without_faces)
        rail = create_cube_without_faces(bm, rail_size, rail_pos, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)


# @map_new_faces(FaceMap.RAILING_POSTS, skip=FaceMap.RAILING_RAILS)
def create_fill_rails(bm, loops, prop):
    pass


# @map_new_faces(FaceMap.RAILING_WALLS)
def create_fill_walls(bm, loops, prop):
    pass


def cross_edge_tangents(edge_a, edge_b):
    return edge_tangent(edge_a).cross(edge_tangent(edge_b))


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

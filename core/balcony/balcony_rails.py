import bpy
import math
import bmesh

from mathutils import Vector
from ...util_rail import (
    add_cube_post,
    align_geometry_to_edge,
    add_posts_between_loops,
    create_cube_without_faces,
    calc_rail_position_and_size_for_loop,
)


def create_balcony_railing(bm, edges, prop, normal):
    balcony_face = {
        f for e in edges for f in e.link_faces if f.normal.z
    }.pop()
    balcony_verts = {v for e in edges for v in e.verts}
    balcony_loops = {l for v in balcony_verts for l in v.link_loops}

    # -- use all loops for making corner posts
    balcony_loops = list(
        l for l in balcony_loops if l.face == balcony_face
    )
    make_corner_posts(bm, balcony_loops, prop, edges, normal)

    # -- remove back loop for creating railing
    balcony_loops = list(
        l for l in balcony_loops if l.edge in edges
    )
    make_fill(bm, balcony_loops, prop)
    bmesh.ops.remove_doubles(bm, verts=bm.verts)


# @map_new_faces(FaceMap.RAILING_POSTS)
def make_corner_posts(bm, loops, prop, edges, normal):
    # add_facemap_for_groups(FaceMap.RAILING_POSTS)

    wall_edge = [l.edge for l in loops if l.edge not in edges].pop()
    for loop in loops:
        v = loop.vert
        e = loop.edge

        vec = loop.calc_tangent()
        width, height = prop.corner_post_width, prop.corner_post_height

        off = vec * math.sqrt(2 * ((width / 2) ** 2))
        pos = v.co + off + Vector((0, 0, height / 2))

        # EDGE CASE
        # -- if this loop.vert belongs to the back edge, we may need to move it back
        # -- by {SLAB_OUTSET} to make it flush with the walls
        active_obj = bpy.context.active_object
        slab_outset = active_obj.tracked_properties.slab_outset
        slab_rel = math.sin(math.pi / 4) * slab_outset
        if v in wall_edge.verts:
            pos += normal * slab_rel

        post = add_cube_post(bm, width, height, pos)
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

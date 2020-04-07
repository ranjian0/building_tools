import bpy
import math
import bmesh

from mathutils import Vector
from ...utils import (
    add_cube_post,
    align_geometry_to_edge,
    add_posts_between_loops,
    create_cube_without_faces,
    calc_rail_position_and_size_for_loop,
)


class RailLoop:
    def __init__(self, **kwargs):
        self.normal = kwargs.get("normal", Vector())
        self.tangent = kwargs.get("tangent", Vector())
        self.angle = kwargs.get("angle", 0.0)

        self.vert = kwargs.get("vert")
        self.edge = kwargs.get("edge")
        self.face = kwargs.get("face")

        self.next = None
        self.prev = None
        self.edge_tangent = Vector()

    def __repr__(self):
        return "RailLoop<loc={}, tangent={}>".format(self.location, self.tangent)

    def _get_loc(self):
        return self.vert.co
    location = property(_get_loc)

    @staticmethod
    def process(loops):
        # -- create rail loops from bm loops
        rl_loops = []
        loop_idx = []
        for loop in loops:
            rl = RailLoop.from_bmloop(loop)
            loop_idx.append(loop.vert.index)
            rl_loops.append(rl)

        # -- set next and previous loops
        for rl, loop in zip(rl_loops, loops):
            loop_n = loop.link_loop_next
            loop_p = loop.link_loop_prev

            rl_loop_n = [l for l in rl_loops if l.vert == loop_n.vert].pop()
            rl.next = rl_loop_n
            rl_loop_p = [l for l in rl_loops if l.vert == loop_p.vert].pop()
            rl.prev = rl_loop_p

            rl.edge_tangent = loop.edge.calc_tangent(loop)

        return rl_loops

    @staticmethod
    def from_bmloop(loop):
        return RailLoop(
            normal=loop.calc_normal(),
            tangent=loop.calc_tangent(),
            angle=loop.calc_angle(),
            vert=loop.vert, edge=loop.edge, face=loop.face
        )


def create_balcony_railing(bm, edges, prop, normal):
    balcony_face = {
        f for e in edges for f in e.link_faces if f.normal.z
    }.pop()
    balcony_verts = {v for e in edges for v in e.verts}

    def loop_is_valid(l):
        return l.edge in edges and l.face == balcony_face
    loops = list({l for v in balcony_verts for l in v.link_loops if loop_is_valid(l)})

    rail_loops = RailLoop.process(balcony_face.loops)
    from pprint import pprint
    # pprint(rail_loops)
    for loop in rail_loops:
        print(loop, " : ", loop.edge_tangent.cross(normal))
        print(loop, " : ", loop.edge_tangent.cross(Vector((0, 0, 1))))
        print()

    make_corner_posts(bm, loops, prop, normal)
    make_fill(bm, loops, prop)
    bmesh.ops.remove_doubles(bm, verts=bm.verts)


# @map_new_faces(FaceMap.RAILING_POSTS)
def make_corner_posts(bm, loops, prop, normal):
    # add_facemap_for_groups(FaceMap.RAILING_POSTS)
    active_obj = bpy.context.active_object
    slab_outset = active_obj.tracked_properties.slab_outset

    def loop_is_last(l):
        e = loop.edge
        return e.calc_tangent(loop).cross(normal).z < 0

    def loop_is_first(l):
        e = loop.edge
        return e.calc_tangent(loop).cross(normal).z > 0

    def post_at_loop(loop):
        vec = loop.calc_tangent()
        width, height = prop.corner_post_width, prop.corner_post_height
        off = vec * math.sqrt(2 * ((width / 2) ** 2))
        if loop_is_first(loop) or loop not in loops:
            # -- pust first and last loops adjacent to walls
            off += normal * slab_outset
        pos = loop.vert.co + off + Vector((0, 0, height / 2))
        post = add_cube_post(bm, width, height, pos)
        align_geometry_to_edge(bm, post, loop.edge)

    last_loop = None
    for loop in loops:
        if loop_is_last(loop):
            last_loop = loop
        post_at_loop(loop)
    if last_loop:
        post_at_loop(last_loop.link_loop_next)


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

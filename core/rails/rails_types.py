import math
import bmesh
import operator
import itertools as it

from mathutils import Vector, Matrix

from bmesh.types import BMVert, BMEdge, BMFace
from ...utils import (
    cube,
    cylinder,
    filter_geom,
    face_with_verts,
    calc_edge_median,
    calc_verts_median,
    boundary_edges_from_face_selection,
)

# TODO:
# Use loops to create fill types


class CreateRailing:
    def __init__(self):
        # -- global state {Wall FILL}
        self.wall_switch = False
        self.corner_angle = 0
        self.num_corners = 1

        # -- global state {remove colinear}
        self.colinear_loops = []

    def from_selection(self, bm, prop):
        """ Creates railing from user selection """
        rail_faces = [f for f in bm.faces if f.select]
        if rail_faces:
            edges = boundary_edges_from_face_selection(bm)
        else:
            # -- user selection is edges
            edges = [e for e in bm.edges if e.select]
            rail_faces = upward_faces_from_edges(edges)

        if len(rail_faces) > 1:
            rail_faces = bmesh.ops.dissolve_faces(bm, faces=rail_faces).get("region")

        self.create_railing(bm, edges, rail_faces, prop)

    def from_edges(self, bm, edges, prop):
        """ Create railing from edges """
        faces_from_edges = upward_faces_from_edges(edges)
        faces_from_edges = [
            f for f in faces_from_edges if all([e in f.edges for e in edges])
        ]

        self.create_railing(bm, edges, faces_from_edges, prop)

    def from_step_edges(self, bm, edges, normal, direction, prop):
        """ Create railing from stair step edges """
        lfaces = upward_faces_from_edges(edges)

        def edge_z(e):
            return calc_edge_median(e).z

        # - find lowest edges
        lowest_edge_z = edge_z(min(edges, key=lambda e: edge_z(e)))
        low_edges = [e for e in edges if round(edge_z(e), 3) == round(lowest_edge_z, 3)]

        # -- add corner post
        for e in low_edges:
            loop = [l for l in e.link_loops if l.face in lfaces][-1]
            cen = calc_edge_median(e)
            tan = e.calc_tangent(loop)
            off = tan * prop.corner_post_width / 2
            pos = cen + off + Vector((0, 0, prop.corner_post_height / 2))

            post = create_cube(
                bm,
                (
                    prop.corner_post_width,
                    prop.corner_post_width,
                    prop.corner_post_height,
                ),
                pos,
            )

            delete_faces(bm, post, bottom=True, top=prop.has_decor)
            if prop.has_decor:
                px, py, pz = pos
                create_cube(
                    bm,
                    (
                        prop.corner_post_width * 2,
                        prop.corner_post_width * 2,
                        prop.corner_post_width / 2,
                    ),
                    (
                        px,
                        py,
                        pz + prop.corner_post_height / 2 + prop.corner_post_width / 4,
                    ),
                )

        # -- add fill types
        if prop.fill == "POSTS":
            other_edges = list(set(edges) - set(low_edges))
            # -- add mid posts
            for e in other_edges:
                loop = [l for l in e.link_loops if l.face in lfaces][-1]
                cen = calc_edge_median(e)
                tan = e.calc_tangent(loop)
                off = tan * prop.corner_post_width / 2
                pos = (
                    cen
                    + off
                    + Vector((0, 0, prop.corner_post_height / 2 - prop.rail_size / 2))
                )

                post = create_cube(
                    bm,
                    (
                        prop.post_size,
                        prop.post_size,
                        prop.corner_post_height - prop.rail_size,
                    ),
                    pos,
                )

            # -- add rail
            rail_groups = []
            if direction == "FRONT":
                ledges = edges[: int(len(edges) / 2)]
                redges = edges[int(len(edges) / 2) :]
                rail_groups.append(ledges)
                rail_groups.append(redges)
            else:
                rail_groups.append(edges)

            for group in rail_groups:
                cen = calc_verts_median([v for e in group for v in e.verts])
                off = Vector((0, 0, prop.corner_post_height))
                pos = cen + off

                length = sum([e.calc_length() for e in group])
                size = (length, 2 * prop.rail_size, prop.rail_size)

                rail = cube(bm, *size)
                bmesh.ops.translate(bm, vec=pos, verts=rail["verts"])
                delete_faces(bm, rail, right=True)

                # --rotate
                bmesh.ops.rotate(
                    bm,
                    verts=rail["verts"],
                    cent=calc_verts_median(rail["verts"]),
                    matrix=Matrix.Rotation(math.atan2(normal.y, normal.x), 4, "Z"),
                )

        elif prop.fill == "RAILS":
            pass
        elif prop.fill == "WALL":
            pass

    def create_railing(self, bm, edges, lfaces, prop):
        """Creates rails and posts along selected edges

        Args:
            bm    (bmesh.types.BMesh): bmesh of current edit mesh
            edges (list): list of edges to create rails along
            *args: items from RailsProperty, see rail_props.py
            **kwargs: Extra kwargs
        """

        loops = []
        for e in edges:
            for v in e.verts:
                if len(v.link_loops) > 1:
                    loops.extend([l for l in v.link_loops if l.face in lfaces])
                else:
                    loops.extend([l for l in v.link_loops])
        loops = list(set(loops))

        if prop.remove_colinear:
            # TODO - make this work on loop with more than two links
            # - remove loops where edges are parallel, and both link_edges are in selection
            is_parallel = lambda loop: round(loop.calc_angle(), 3) == 3.142
            is_middle = lambda loop: (
                loop.link_loop_next in loops and loop.link_loop_prev in loops
            )

            self.colinear_loops.extend(
                [l for l in loops if (is_parallel(l) and is_middle(l))]
            )
            loops = [l for l in loops if not (is_parallel(l) and is_middle(l))]

        self.create_corner_post(bm, loops, prop)
        self.create_fill(bm, edges, prop)
        bmesh.ops.remove_doubles(bm, verts=bm.verts)

    def create_corner_post(self, bm, loops, prop):
        """ Create Corner posts """
        for loop in loops:
            v = loop.vert
            e = loop.edge

            vec = loop.calc_tangent()
            width, height = prop.corner_post_width, prop.corner_post_height

            angle = loop.calc_angle()
            segments = polygon_sides_from_angle(angle)
            if segments == 4 or segments < 0:  # - (90 or 180)
                off = vec * math.sqrt(2 * ((width / 2) ** 2))
                pos = v.co + off + Vector((0, 0, height / 2))
                post = add_cube_post(bm, width, height, pos, prop.has_decor)
            else:
                pos = v.co + (vec * width) + Vector((0, 0, height / 2))
                post = create_cylinder(bm, width / 2, height, segments, pos)

                # -- store global state
                self.wall_switch = True
                self.num_corners = segments
                self.corner_angle = math.pi - angle

            align_geometry_to_edge(bm, post, e)

    def create_fill(self, bm, edges, prop):
        """ Create fill types for railing """
        for edge in edges:
            if prop.fill == "RAILS":
                self.create_fill_rails(bm, edge, prop)
            elif prop.fill == "POSTS":
                self.create_fill_posts(bm, edge, prop)
            elif prop.fill == "WALL":
                self.create_fill_walls(bm, edge, prop)

    def create_fill_rails(self, bm, edge, prop):
        tan = edge_tangent(edge)
        off = tan.normalized() * (prop.corner_post_width / 2)
        start = calc_edge_median(edge) + off
        stop = calc_edge_median(edge) + off + Vector((0, 0, prop.corner_post_height))
        if prop.expand:
            size = (edge.calc_length(), prop.rail_size, prop.rail_size)
        else:
            size = (
                edge.calc_length() - (prop.corner_post_width * 2),
                prop.rail_size,
                prop.rail_size,
            )

        rail = cube(bm, *size)
        delete_faces(bm, rail, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)

        rail_count = int((prop.corner_post_height / prop.rail_size) * prop.rail_density)
        array_elements(bm, rail, rail_count, start, stop)

    def create_fill_posts(self, bm, edge, prop):
        v1, v2 = sort_edge_verts_by_orientation(edge)
        vec = (v2.co - v1.co).normalized()
        tan = edge_tangent(edge).normalized()

        # -- add posts
        off = tan * (prop.corner_post_width / 2)
        height_v = Vector((0, 0, prop.corner_post_height / 2 - prop.rail_size / 2))
        size = (
            prop.post_size,
            prop.post_size,
            prop.corner_post_height - prop.rail_size,
        )

        post = cube(bm, *size)
        delete_faces(bm, post, top=True, bottom=True)
        align_geometry_to_edge(bm, post, edge)

        gap = vec * prop.corner_post_width / 2
        start = v1.co + off + height_v + gap
        stop = v2.co + off + height_v - gap
        length = edge.calc_length() - prop.corner_post_width
        post_count = round((length / prop.post_size) * prop.post_density)
        array_elements(bm, post, post_count, start, stop)

        # fill gaps created by remove colinear
        if self.colinear_loops:
            # -- fill spaces created by no corner posts
            for loop in self.colinear_loops:
                if loop.edge != edge:
                    continue

                v = loop.vert
                p = v.co + off + height_v
                fill_post = create_cube(bm, size, p)
                delete_faces(bm, fill_post, top=True, bottom=True)

        # -- add top rail
        pinch = 0.01  # offset to prevent z-buffer fighting
        rail_pos = (
            calc_edge_median(edge)
            + off
            + Vector((0, 0, prop.corner_post_height - prop.rail_size / 2 - pinch))
        )
        size = (edge.calc_length(), 2 * prop.rail_size, prop.rail_size)

        rail = create_cube(bm, size, rail_pos)
        delete_faces(bm, rail, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)

    def create_fill_walls(self, bm, edge, prop):
        off = prop.corner_post_width
        if self.wall_switch:
            # - a cylinder corner post was created, determine length of side with cosine rule
            val_a = 2 * (prop.corner_post_width ** 2)
            val_b = val_a * math.cos(self.corner_angle)
            off = math.sqrt(val_a - val_b)

        v1, v2 = edge.verts
        _dir = (v1.co - v2.co).normalized()
        tan = edge_tangent(edge)

        if self.wall_switch:  # -- only for cylider corner posts
            start = v1.co - (_dir * off)
            end = v2.co + (_dir * off)
        else:
            if prop.expand:
                start = v1.co
                end = v2.co
            else:
                start = v1.co - (_dir * off)
                end = v2.co + (_dir * off)

        create_wall(bm, start, end, prop.corner_post_height, prop.wall_width, tan)


def edge_tangent(edge):
    """ Find the tangent of an edge """
    tan = None
    for l in edge.link_loops:
        t = edge.calc_tangent(l)
        if not round(t.z):
            tan = t
    return tan


def create_cube(bm, size, position):
    """ Create cube with size and at position"""
    post = cube(bm, *size)
    bmesh.ops.translate(bm, verts=post["verts"], vec=position)
    return post


def create_cylinder(bm, radius, height, segs, position):
    """ Create cylinder at pos"""
    cy = cylinder(bm, radius, height, segs)
    bmesh.ops.translate(bm, verts=cy["verts"], vec=position)
    return cy


def create_wall(bm, start, end, height, width, tangent):
    """ Extrude a wall of height from start to end """
    start_edge = create_edge(bm, start, start + Vector((0, 0, height)))

    res = bmesh.ops.extrude_edge_only(bm, edges=[start_edge])
    bmesh.ops.translate(bm, vec=end - start, verts=filter_geom(res["geom"], BMVert))

    if width:
        face = filter_geom(res["geom"], BMFace)[-1]
        if face.normal.to_tuple(3) != tangent.to_tuple(3):
            face.normal_flip()
        n = face.normal

        res = bmesh.ops.extrude_face_region(bm, geom=[face])
        bmesh.ops.translate(bm, vec=-n * width, verts=filter_geom(res["geom"], BMVert))

        # delete hidden geom
        edges = filter_geom(res["geom"], BMEdge)
        faces = [
            f
            for e in edges
            for f in e.link_faces
            if not f.normal.z and f not in filter_geom(res["geom"], BMFace)
        ]
        bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")


def delete_faces(bm, post, **directions):
    """ Delete flagged faces for the given post (cube geometry) """

    def D(direction):
        return directions.get(direction, False)

    vts = post["verts"]
    keys = ["z", "z", "x", "x", "y", "y"]
    dirs = [D("top"), D("bottom"), D("left"), D("right"), D("front"), D("back")]
    slcs = it.chain.from_iterable(it.repeat([slice(4, 8), slice(4)], 3))

    faces = []
    for direction, key, _slice in zip(dirs, keys, slcs):
        if direction:
            vts.sort(key=lambda v: getattr(v.co, key))
            faces.append(face_with_verts(bm, vts[_slice]))

    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")


def array_elements(bm, elem, count, start, stop):
    """ Duplicate elements count-1 times between start and stop """
    step = (stop - start) / (count+1)
    for i in range(count):
        if i == 0:
            bmesh.ops.translate(bm, verts=elem["verts"], vec=start + step)
        else:
            faces = list({f for v in elem["verts"] for f in v.link_faces})
            ret = bmesh.ops.duplicate(bm, geom=faces)
            bmesh.ops.translate(
                bm, verts=filter_geom(ret["geom"], BMVert), vec=step * i
            )


def upward_faces_from_edges(edges):
    verts = list({v for e in edges for v in e.verts})
    return list({f for v in verts for f in v.link_faces if f.normal.z})


def create_edge(bm, start, end):
    start_vert = bm.verts.new(start)
    end_vert = bm.verts.new(end)
    return bm.edges.new((start_vert, end_vert))


def add_cube_post(bm, width, height, position, has_decor):
    post = create_cube(bm, (width, width, height), position)

    delete_faces(bm, post, bottom=True, top=has_decor)
    if has_decor:
        px, py, pz = position
        pz += height / 2 + width / 4
        create_cube(bm, (width * 2, width * 2, width / 2), (px, py, pz))
    return post


def align_geometry_to_edge(bm, geom, edge):
    v1, v2 = edge.verts
    dx, dy = (v1.co - v2.co).normalized().xy
    bmesh.ops.rotate(
        bm,
        verts=geom["verts"],
        cent=calc_verts_median(geom["verts"]),
        matrix=Matrix.Rotation(math.atan2(dy, dx), 4, "Z"),
    )


def polygon_sides_from_angle(angle):
    return round((2 * math.pi) / (math.pi - angle))


def sort_edge_verts_by_orientation(edge):
    start, end = edge.verts
    orient = end.co - start.co
    if orient.x:
        start, end = sorted(edge.verts, key=operator.attrgetter("co.x"))
    elif orient.y:
        start, end = sorted(edge.verts, key=operator.attrgetter("co.y"))
    return start, end

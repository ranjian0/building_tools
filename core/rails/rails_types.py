import math
import bmesh
import operator
import itertools as it

from mathutils import Vector, Matrix

from bmesh.types import BMVert, BMEdge, BMFace
from ...utils import (
    cube,
    select,
    cylinder,
    filter_geom,
    face_with_verts,
    calc_edge_median,
    calc_verts_median,
    boundary_edges_from_face_selection,
)


class RailingData:
    def __init__(self):
        self.wall_switch = False
        self.corner_angle = 0
        self.num_corners = 1
        self.colinear_loops = []

    def __repr__(self):
        return (
            f"Wall Switch   >-{self.wall_switch}\n"
            + f"Corner Angle  >-{self.corner_angle}\n"
            + f"Num Corners   >-{self.num_corners}\n"
            + f"Loops         >-{self.colinear_loops}"
        )


def create_railing_from_selection(bm, prop):
    rail_faces = [f for f in bm.faces if f.select]
    if rail_faces:
        edges = boundary_edges_from_face_selection(bm)
    else:
        edges = [e for e in bm.edges if e.select]
        rail_faces = upward_faces_from_edges(edges)

    if len(rail_faces) > 1:
        rail_faces = bmesh.ops.dissolve_faces(bm, faces=rail_faces).get("region")
    select(rail_faces, False)
    create_railing(bm, edges, rail_faces, prop, RailingData())


def create_railing_from_edges(bm, edges, prop):
    faces_from_edges = upward_faces_from_edges(edges)
    faces_from_edges = [
        f for f in faces_from_edges if all([e in f.edges for e in edges])
    ]
    create_railing(bm, edges, faces_from_edges, prop, RailingData())


def create_railing_from_step_edges(bm, edges, normal, prop):
    if prop.rail.fill == "POSTS":
        fill_posts_for_step_edges(bm, edges, normal, prop)
    elif prop.rail.fill == "RAILS":
        pass
    elif prop.rail.fill == "WALL":
        pass


def create_railing(bm, edges, lfaces, prop, raildata):
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
        def is_parallel(loop):
            return round(loop.calc_angle(), 3) == 3.142

        def is_middle(loop):
            return loop.link_loop_next in loops and loop.link_loop_prev in loops

        raildata.colinear_loops.extend(
            [l for l in loops if (is_parallel(l) and is_middle(l))]
        )
        loops = [l for l in loops if not (is_parallel(l) and is_middle(l))]

    create_corner_post(bm, loops, prop, raildata)
    create_fill(bm, edges, prop, raildata)
    bmesh.ops.remove_doubles(bm, verts=bm.verts)


def create_corner_post(bm, loops, prop, raildata):
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
            raildata.wall_switch = True
            raildata.num_corners = segments
            raildata.corner_angle = math.pi - angle

        align_geometry_to_edge(bm, post, e)


def create_fill(bm, edges, prop, raildata):
    """ Create fill types for railing """
    for edge in edges:
        if prop.fill == "WALL":
            create_fill_walls(bm, edge, prop, raildata)

    if prop.fill == "POSTS":
        create_fill_posts(bm, edges, prop, raildata)
    elif prop.fill == "RAILS":
        create_fill_rails(bm, edges, prop)


def create_fill_rails(bm, edges, prop):
    loops = loops_from_edges(edges)

    for loop in loops:
        edge = loop.edge
        if edge not in edges:
            continue

        rail_pos, rail_size = calc_rail_position_and_size_for_loop(loop, prop)

        start = rail_pos
        stop = rail_pos + Vector((0, 0, prop.corner_post_height-prop.rail_size))

        rail = cube(bm, *rail_size)
        delete_faces(bm, rail, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)
        rail_count = int((prop.corner_post_height / prop.rail_size) * prop.rail_density)
        array_elements(bm, rail, rail_count, start, stop)

        # -- create top rail
        rail = create_cube(bm, rail_size, stop + Vector((0, 0, prop.rail_size/2)))
        delete_faces(bm, rail, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)


def create_fill_posts(bm, edges, prop, raildata):
    loops = loops_from_edges(edges)

    for loop in loops:
        edge = loop.edge
        if edge not in edges:
            continue

        # -- add posts
        add_posts_between_loops(bm, [loop, loop.link_loop_next], prop)

        # -- fill gaps created by remove colinear
        fill_post_for_colinear_gap(bm, edge, prop, raildata)

        # -- add top rail
        rail_pos, rail_size = calc_rail_position_and_size_for_loop(loop, prop)
        rail_pos += Vector((0, 0, prop.corner_post_height - prop.rail_size / 2))

        rail = create_cube(bm, rail_size, rail_pos)
        delete_faces(bm, rail, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)


def create_fill_walls(bm, edge, prop, raildata):
    off = prop.corner_post_width
    if raildata.wall_switch:
        # - a cylinder corner post was created, determine length of side with cosine rule
        val_a = 2 * (prop.corner_post_width ** 2)
        val_b = val_a * math.cos(raildata.corner_angle)
        off = math.sqrt(val_a - val_b)

    v1, v2 = edge.verts
    _dir = (v1.co - v2.co).normalized()
    tan = edge_tangent(edge)

    if raildata.wall_switch:
        # -- only for cylider corner posts
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
    step = (stop - start) / (count + 1)
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


def add_posts_between_loops(bm, loops, prop):
    loop_a, loop_b = loops
    edge = loop_a.edge

    # -- create post geometry
    height_v = Vector((0, 0, prop.corner_post_height / 2 - prop.rail_size / 2))
    size = (prop.post_size, prop.post_size, prop.corner_post_height - prop.rail_size)
    post = cube(bm, *size)
    delete_faces(bm, post, top=True, bottom=True)
    align_geometry_to_edge(bm, post, edge)

    # -- add posts array between loop_a and loop_b
    off_a = loop_a.calc_tangent() * (prop.corner_post_width * 0.75)
    start = loop_a.vert.co + off_a + height_v

    off_b = loop_b.calc_tangent() * (prop.corner_post_width * 0.75)
    stop = loop_b.vert.co + off_b + height_v

    length = edge.calc_length()
    post_count = round((length / prop.post_size) * prop.post_density)
    array_elements(bm, post, post_count, start, stop)


def fill_post_for_colinear_gap(bm, edge, prop, raildata):
    off = edge_tangent(edge).normalized() * (prop.corner_post_width / 2)
    height_v = Vector((0, 0, prop.corner_post_height / 2 - prop.rail_size / 2))
    size = (prop.post_size, prop.post_size, prop.corner_post_height - prop.rail_size)
    if raildata.colinear_loops:
        # -- fill spaces created by no corner posts
        for loop in raildata.colinear_loops:
            if loop.edge != edge:
                continue

            v = loop.vert
            p = v.co + off + height_v
            fill_post = create_cube(bm, size, p)
            delete_faces(bm, fill_post, top=True, bottom=True)


def fill_posts_for_step_edges(bm, edges, normal, prop):
    """ Add posts for stair edges """

    edge_groups = get_edge_groups_from_direction(edges, prop.stair_direction)
    for group in edge_groups:
        #   -- max and min coordinate for step edges
        min_location, max_location = find_min_and_max_vert_locations(
            [vert for edge in group for vert in edge.verts], normal
        )

        #  -- slope and edge tangent
        slope = slope_between_vectors(max_location, min_location, normal)
        tangent = edge_tangent(group[-1]).normalized()

        #   -- fill posts along each edge that get taller along slope
        for edge in group:
            add_posts_along_edge_with_slope(bm, edge, slope, normal, tangent, prop.rail)

        #   --  add a rail from min_location to max_location using slope
        height = prop.rail.corner_post_height - (prop.rail.rail_size / 2)
        offset = (tangent * prop.rail.rail_size) + Vector((0, 0, height))
        start = max_location + offset
        end = min_location + offset
        add_rail_with_slope(bm, start, end, slope, normal, prop.rail)


def get_edge_groups_from_direction(edges, direction):
    edge_groups = []
    if direction == "FRONT":
        left_edges = edges[: int(len(edges) / 2)]
        right_edges = edges[int(len(edges) / 2) :]
        edge_groups.append(left_edges)
        edge_groups.append(right_edges)
    else:
        edge_groups.append(edges)
    return edge_groups


def slope_between_vectors(start, end, normal):
    change_z = start.z - end.z
    if normal.x:
        change_other = start.x - end.x
    elif normal.y:
        change_other = start.y - end.y
    else:
        return 1
    return change_z / change_other


def find_min_and_max_vert_locations(verts, normal):
    v_location = [vert.co.copy() for vert in verts]
    sort_key = operator.attrgetter("x" if normal.x else "y")
    res = [function(v_location, key=sort_key) for function in (min, max)]
    if sort_key(normal) > 0:
        return res
    return reversed(res)


def normalized_edge_vector(edge):
    v1, v2 = edge.verts
    return (v2.co - v1.co).normalized()


def add_posts_along_edge_with_slope(bm, edge, slope, normal, tangent, prop):
    post_count = round((edge.calc_length() / prop.post_size) * prop.post_density)
    post_spacing = edge.calc_length() / post_count
    post_height = prop.corner_post_height - prop.rail_size

    vec = normalized_edge_vector(edge)
    tan_offset = tangent * prop.corner_post_width / 2
    post_offset = tan_offset + (-normal * prop.post_size / 2)

    end, start = find_min_and_max_vert_locations(edge.verts, normal)
    for i in range(post_count):
        height = post_height + abs(slope * (i * post_spacing))
        position = start + post_offset - (vec * (i * post_spacing))
        position += Vector((0, 0, height / 2))
        size = (prop.post_size,) * 2 + (height,)
        create_cube(bm, size, position)


def add_rail_with_slope(bm, start, end, slope, normal, prop):
    length = (start - end).length + prop.rail_size
    size = (length, 2 * prop.rail_size, prop.rail_size)
    position = start.lerp(end, 0.5) - ((end - start).normalized() * prop.rail_size / 2)

    rail = create_cube(bm, size, position)
    delete_faces(bm, rail, right=True)

    bmesh.ops.rotate(
        bm,
        verts=rail["verts"],
        cent=calc_verts_median(rail["verts"]),
        matrix=Matrix.Rotation(math.atan2(normal.y, normal.x), 4, "Z"),
    )

    axis = "Y" if normal.x else "X"
    slope *= 1 if normal.y else -1  # -- figure out why???
    bmesh.ops.rotate(
        bm,
        verts=rail["verts"],
        cent=calc_verts_median(rail["verts"]),
        matrix=Matrix.Rotation(math.atan(slope), 4, axis),
    )


def edge_vector(edge):
    v1, v2 = edge.verts
    return (v2.co - v1.co).normalized()


def loops_from_edges(edges):
    lfaces = upward_faces_from_edges(edges)
    loops = []
    for e in edges:
        for v in e.verts:
            if len(v.link_loops) > 1:
                loops.extend([l for l in v.link_loops if l.face in lfaces])
            else:
                loops.extend([l for l in v.link_loops])
    return list(set(loops))


def calc_rail_position_and_size_for_loop(loop, prop):
    edge = loop.edge
    off = edge_tangent(edge).normalized() * (prop.corner_post_width / 2)
    convex_loops = [l.is_convex for l in (loop, loop.link_loop_next)]
    num_convex = sum(convex_loops)
    convex_offset = edge_vector(edge) * (
        prop.corner_post_width / 2 * (2 - num_convex)
    )
    convex_offset *= 1 if convex_loops[0] else -1
    convex_offset *= 0 if num_convex == 0 else 1

    rail_pos = calc_edge_median(edge) + off + convex_offset
    rail_len = edge.calc_length() - prop.corner_post_width * num_convex
    rail_size = (rail_len, 2 * prop.rail_size, prop.rail_size)
    return rail_pos, rail_size

import math
import bmesh
import operator
import functools

from mathutils import Vector, Matrix

from bmesh.types import BMVert, BMEdge, BMFace
from ...utils import (
    select,
    FaceMap,
    validate,
    filter_geom,
    create_cube,
    edge_vector,
    edge_tangent,
    map_new_faces,
    create_cylinder,
    calc_edge_median,
    calc_verts_median,
    add_facemap_for_groups,
    create_cube_without_faces,
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
    """ create railing from what user has selected
    """
    rail_faces = [f for f in bm.faces if f.select]
    if rail_faces:
        edges = boundary_edges_from_face_selection(bm)
    else:
        edges = [e for e in bm.edges if e.select]
        rail_faces = upward_faces_from_edges(edges)
        rail_faces = [
            f for f in rail_faces if all([e in f.edges for e in edges])
        ]

    if len(rail_faces) > 1:
        rail_faces = bmesh.ops.dissolve_faces(bm, faces=rail_faces).get("region")
    select(rail_faces, False)
    create_railing(bm, edges, rail_faces, prop, RailingData())


def create_railing_from_edges(bm, edges, prop):
    """ Create railing along edges
    """
    faces_from_edges = upward_faces_from_edges(edges)
    faces_from_edges = [
        f for f in faces_from_edges if all([e in f.edges for e in edges])
    ]
    create_railing(bm, edges, faces_from_edges, prop, RailingData())


def create_railing_from_step_edges(bm, edges, normal, prop):
    """ Create railing from stairs
    """
    if prop.rail.fill == "POSTS":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_RAILS))
        fill_posts_for_step_edges(bm, edges, normal, prop)
    elif prop.rail.fill == "RAILS":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_RAILS))
        fill_rails_for_step_edges(bm, edges, normal, prop)
    elif prop.rail.fill == "WALL":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_WALLS))
        fill_walls_for_step_edges(bm, edges, normal, prop)


def create_railing(bm, edges, lfaces, prop, raildata):
    """ Perform all railing procedures
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
        def is_middle(loop):
            return loop.link_loop_next in loops and loop.link_loop_prev in loops

        raildata.colinear_loops.extend(
            [l for l in loops if (is_parallel(l) and is_middle(l))]
        )
        loops = [l for l in loops if not (is_parallel(l) and is_middle(l))]

    create_corner_post(bm, loops, prop, raildata)
    create_fill(bm, edges, prop, raildata)
    bmesh.ops.remove_doubles(bm, verts=bm.verts)


@map_new_faces(FaceMap.RAILING_POSTS)
def create_corner_post(bm, loops, prop, raildata):
    """ Add post at each vert in loops
    """
    add_facemap_for_groups(FaceMap.RAILING_POSTS)
    for loop in loops:
        v = loop.vert
        e = loop.edge

        vec = loop.calc_tangent()
        width, height = prop.corner_post_width, prop.corner_post_height

        angle = loop.calc_angle()
        segments = polygon_sides_from_angle(angle)
        if segments == 4 or segments < 0:  # - (90 or 180)
            off = vec * math.sqrt(2 * ((width / 2) ** 2))
            if is_parallel(loop):
                off = vec * (width / 2)
            pos = v.co + off + Vector((0, 0, height / 2))
            post = add_cube_post(bm, width, height, pos)
        else:
            pos = v.co + (vec * width) + Vector((0, 0, height / 2))
            post = create_cylinder(bm, width, height, segments, pos)

            # -- store global state
            raildata.wall_switch = True
            raildata.num_corners = segments
            raildata.corner_angle = math.pi - angle

        align_geometry_to_edge(bm, post, e)


def create_fill(bm, edges, prop, raildata):
    """ Create fill types for railing
    """
    if prop.fill == "POSTS":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_RAILS))
        create_fill_posts(bm, edges, prop, raildata)
    elif prop.fill == "RAILS":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_RAILS))
        create_fill_rails(bm, edges, prop)
    elif prop.fill == "WALL":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_WALLS))
        create_fill_walls(bm, edges, prop, raildata)


@map_new_faces(FaceMap.RAILING_RAILS)
def create_fill_rails(bm, edges, prop):
    """ Add rails between corner posts
    """
    loops = loops_from_edges(edges)

    processed_edges = []
    for loop in loops:
        edge = loop.edge
        if edge not in edges or edge in processed_edges:
            continue

        rail_pos, rail_size = calc_rail_position_and_size_for_loop(loop, prop)

        start = rail_pos
        stop = rail_pos + Vector((0, 0, prop.corner_post_height - prop.rail_size))

        rail = create_cube_without_faces(bm, rail_size, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)
        rail_count = int((prop.corner_post_height / prop.rail_size) * prop.rail_density)
        array_elements(bm, rail, rail_count, start, stop)

        # -- create top rail
        p = stop + Vector((0, 0, prop.rail_size / 2))
        rail = create_cube_without_faces(bm, rail_size, p, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)
        processed_edges.append(edge)


@map_new_faces(FaceMap.RAILING_POSTS, skip=FaceMap.RAILING_RAILS)
def create_fill_posts(bm, edges, prop, raildata):
    """ Add posts between corner posts
    """
    loops = loops_from_edges(edges)

    processed_edges = []
    for loop in loops:
        edge = loop.edge
        if edge not in edges or edge in processed_edges:
            continue

        # -- add posts
        add_posts_between_loops(bm, [loop, loop.link_loop_next], prop)

        # -- fill gaps created by remove colinear
        fill_post_for_colinear_gap(bm, edge, prop, raildata)

        # -- add top rail
        rail_pos, rail_size = calc_rail_position_and_size_for_loop(loop, prop)
        rail_pos += Vector((0, 0, prop.corner_post_height - prop.rail_size / 2))

        rail = map_new_faces(FaceMap.RAILING_RAILS)(create_cube_without_faces)
        rail = rail(bm, rail_size, rail_pos, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)
        processed_edges.append(edge)


@map_new_faces(FaceMap.RAILING_WALLS)
def create_fill_walls(bm, edges, prop, raildata):
    """ Add walls between corner posts
    """
    loops = loops_from_edges(edges)

    for loop in loops:
        edge = loop.edge
        if edge not in edges:
            continue

        off = prop.corner_post_width
        if raildata.wall_switch:
            # - a cylinder corner post was created, determine length of side with cosine rule
            val_a = 2 * (prop.corner_post_width ** 2)
            val_b = val_a * math.cos(raildata.corner_angle)
            off = math.sqrt(val_a - val_b)

        loop_a, loop_b = loop, loop.link_loop_next
        vec = (loop_a.vert.co - loop_b.vert.co).normalized()
        off_a = (vec * off) if loop_a.is_convex else Vector()
        off_b = (vec * off) if loop_b.is_convex else Vector()

        start = loop_a.vert.co - off_a
        end = loop_b.vert.co + off_b
        wall = create_wall(
            bm, start, end, prop.corner_post_height, prop.wall_width, edge_tangent(edge)
        )
        wall(delete_faces=["bottom", "left", "right"])


def create_wall(bm, start, end, height, width, tangent):
    """ Extrude a wall of height from start to end
    """
    start_edge = create_edge(bm, start, start + Vector((0, 0, height)))

    res = bmesh.ops.extrude_edge_only(bm, edges=[start_edge])
    bmesh.ops.translate(bm, vec=end - start, verts=filter_geom(res["geom"], BMVert))

    if width:
        face = filter_geom(res["geom"], BMFace).pop()
        if face.normal.to_tuple(3) != tangent.to_tuple(3):
            face.normal_flip()
        n = face.normal

        res = bmesh.ops.extrude_face_region(bm, geom=[face])
        bmesh.ops.translate(bm, vec=-n * width, verts=filter_geom(res["geom"], BMVert))

        # delete hidden faces
        edges = filter_geom(res["geom"], BMEdge)
        return functools.partial(delete_linked_wall_faces, bm, edges, tangent)
    return lambda **kwargs: None


def delete_linked_wall_faces(bm, edges, tangent, delete_faces=["bottom"]):
    """ Delete faces linked to edges with normal flagged in delete_faces
    """
    faces = [f for e in edges for f in e.link_faces]
    faces_to_delete = []
    if "bottom" in delete_faces:
        faces_to_delete.extend([f for f in faces if f.normal.z < 0])

    n = tangent.cross(Vector((0, 0, 1)))
    attr = "x" if n.x else "y"
    if "left" in delete_faces:
        faces_to_delete.extend([f for f in faces if getattr(f.normal, attr) < 0])
    if "right" in delete_faces:
        faces_to_delete.extend([f for f in faces if getattr(f.normal, attr) > 0])

    bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES_ONLY")
    return validate(faces)


def is_parallel(loop):
    """ Determine if this loop's vert is between parallel edges
    """
    return math.isclose(loop.calc_angle(), math.pi, rel_tol=1e-04)


def array_elements(bm, elem, count, start, stop):
    """ Duplicate elements count-1 times between start and stop
    """
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
    """ Find linked upward facing faces
    """
    verts = list({v for e in edges for v in e.verts})
    return list({f for v in verts for f in v.link_faces if f.normal.z})


def create_edge(bm, start, end):
    """ Create and edge between start and end
    """
    start_vert = bm.verts.new(start)
    end_vert = bm.verts.new(end)
    return bm.edges.new((start_vert, end_vert))


def add_cube_post(bm, width, height, position):
    """ Create cube geometry at position
    """
    post = create_cube_without_faces(
        bm, (width, width, height), position, bottom=True
    )
    return post


def align_geometry_to_edge(bm, geom, edge):
    """ Orient geom along an edge
    """
    v1, v2 = edge.verts
    dx, dy = (v1.co - v2.co).normalized().xy
    bmesh.ops.rotate(
        bm,
        verts=geom["verts"],
        cent=calc_verts_median(geom["verts"]),
        matrix=Matrix.Rotation(math.atan2(dy, dx), 4, "Z"),
    )


def polygon_sides_from_angle(angle):
    """ Determine the number of sides for a polygon with an interior angle 'angle'
    """
    return round((2 * math.pi) / (math.pi - angle))


def sort_edge_verts_by_orientation(edge):
    """ Sort the verts in an edge based on the axis its parallel to
    """
    start, end = edge.verts
    orient = end.co - start.co
    if orient.x:
        start, end = sorted(edge.verts, key=operator.attrgetter("co.x"))
    elif orient.y:
        start, end = sorted(edge.verts, key=operator.attrgetter("co.y"))
    return start, end


def add_posts_between_loops(bm, loops, prop):
    """ Create array for posts between loop verts
    """
    loop_a, loop_b = loops
    edge = loop_a.edge

    # -- create post geometry
    height_v = Vector((0, 0, prop.corner_post_height / 2 - prop.rail_size / 2))
    size = (prop.post_size, prop.post_size, prop.corner_post_height - prop.rail_size)
    post = create_cube_without_faces(bm, size, top=True, bottom=True)
    align_geometry_to_edge(bm, post, edge)

    # -- add posts array between loop_a and loop_b
    def loop_factor(loop):
        return 0.5 if is_parallel(loop) else 0.75

    off_a = loop_a.calc_tangent() * (prop.corner_post_width * loop_factor(loop_a))
    start = loop_a.vert.co + off_a + height_v

    off_b = loop_b.calc_tangent() * (prop.corner_post_width * loop_factor(loop_b))
    stop = loop_b.vert.co + off_b + height_v

    length = edge.calc_length()
    post_count = round((length / prop.post_size) * prop.post_density)
    array_elements(bm, post, post_count, start, stop)


def fill_post_for_colinear_gap(bm, edge, prop, raildata):
    """ Add a post where corner posts were removed due to belonging to
    co-linear loops
    """
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
            create_cube_without_faces(bm, size, p, top=True, bottom=True)


@map_new_faces(FaceMap.RAILING_POSTS, skip=FaceMap.RAILING_RAILS)
def fill_posts_for_step_edges(bm, edges, normal, prop):
    """ Add posts for stair edges
    """
    edge_groups = get_edge_groups_from_direction(edges, prop.stair_direction)
    for group in edge_groups:
        #   -- max and min coordinate for step edges
        min_location, max_location = find_min_and_max_vert_locations(
            [vert for edge in group for vert in edge.verts], normal
        )
        step_size = abs((max_location.z - min_location.z) / (prop.step_count - 1))
        min_location.z += step_size

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


@map_new_faces(FaceMap.RAILING_RAILS, skip=FaceMap.RAILING_POSTS)
def fill_rails_for_step_edges(bm, edges, normal, prop):
    """ Add rails for stair edges
    """
    rail = prop.rail
    edge_groups = get_edge_groups_from_direction(edges, prop.stair_direction)
    for group in edge_groups:
        #   -- max and min coordinate for step edges
        min_location, max_location = find_min_and_max_vert_locations(
            [vert for edge in group for vert in edge.verts], normal
        )

        step_size = (max_location.z - min_location.z) / (prop.step_count - 1)
        max_location.z += step_size

        #  -- slope and edge tangent
        tangent = edge_tangent(group[-1]).normalized()
        tangent_offset = tangent * rail.corner_post_width / 2
        slope = slope_between_vectors(max_location, min_location, normal)

        #  -- add corner post at max location
        post_w, post_h = rail.corner_post_width, rail.corner_post_height
        post_pos = max_location + Vector((0, 0, post_h / 2 - step_size))
        post_pos += tangent_offset + (normal * -post_w / 2)

        post = map_new_faces(FaceMap.RAILING_POSTS)(add_cube_post)
        post(bm, post_w, post_h, post_pos)

        #   --  add a rails
        array_sloped_rails(
            bm, min_location, max_location, step_size, slope, normal, tangent, rail
        )


@map_new_faces(FaceMap.RAILING_WALLS)
def fill_walls_for_step_edges(bm, edges, normal, prop):
    """ Add wall for stair edges
    """
    rail = prop.rail
    edge_groups = get_edge_groups_from_direction(edges, prop.stair_direction)
    for group in edge_groups:
        min_location, max_location = find_min_and_max_vert_locations(
            [vert for edge in group for vert in edge.verts], normal
        )
        step_size = abs((max_location.z - min_location.z) / (prop.step_count - 1))

        for edge in group:
            tan = edge_tangent(edge)
            start, end = [v.co for v in edge.verts]
            wall = create_wall(
                bm, start, end, rail.corner_post_height, rail.wall_width, tan
            )
            inner = "right" if sum(normal) < 0 else "left"
            faces = wall(delete_faces=["bottom", inner])

            up_faces = [f for f in faces if f.normal.z > 0]
            slope_step_walls(bm, up_faces, normal, step_size)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)


def get_edge_groups_from_direction(edges, direction):
    """ separate the edges based on given direction
    see stairs_types.py to see how edge groups are formed
    """
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
    """ Calculate the slope between start and end
    switch the 'run' based on normal for 'slope = rise/run'
    """
    change_z = start.z - end.z
    if normal.x:
        change_other = start.x - end.x
    elif normal.y:
        change_other = start.y - end.y
    else:
        return 1
    return change_z / change_other


def find_min_and_max_vert_locations(verts, normal):
    """ Find the minimum and maximum location in verts based on normal direction
    """
    v_location = [vert.co.copy() for vert in verts]
    sort_key = operator.attrgetter("x" if normal.x else "y")
    res = [function(v_location, key=sort_key) for function in (min, max)]
    if sort_key(normal) > 0:
        return res
    return reversed(res)


def add_posts_along_edge_with_slope(bm, edge, slope, normal, tangent, prop):
    """
    Add posts along an edge with increasing height based on slope
    """
    post_count = round((edge.calc_length() / prop.post_size) * prop.post_density)
    post_spacing = edge.calc_length() / post_count
    post_height = prop.corner_post_height - (prop.rail_size / 2)

    vec = edge_vector(edge)
    tan_offset = tangent * prop.corner_post_width / 2
    post_offset = tan_offset + (-normal * prop.post_size / 2)

    end, start = find_min_and_max_vert_locations(edge.verts, normal)
    for i in range(post_count):
        height = post_height + abs(slope * (i * post_spacing))
        position = start + post_offset - (vec * (i * post_spacing))
        position += Vector((0, 0, height / 2))
        size = (prop.post_size,) * 2 + (height,)
        create_cube(bm, size, position)


@map_new_faces(FaceMap.RAILING_RAILS)
def add_rail_with_slope(bm, start, end, slope, normal, prop):
    """ Add a rail from start to end with a given slope
    """
    length = (start - end).length + prop.rail_size
    size = (length, 2 * prop.rail_size, prop.rail_size)
    position = start.lerp(end, 0.5) - ((end - start).normalized() * prop.rail_size / 2)
    position += -normal * 0.0025  # MAGIC - moves the rail abit to remove empty gaps

    rail = create_cube_without_faces(bm, size, position, right=True)

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


def loops_from_edges(edges):
    """ Get all the loops that bound edges with upward faces
    """
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
    """ Add a rail with proper position and size along the loop's edge
    """
    edge = loop.edge
    off = edge_tangent(edge).normalized() * (prop.corner_post_width / 2)
    convex_loops = [l.is_convex for l in (loop, loop.link_loop_next)]
    num_convex = sum(convex_loops)
    convex_offset = edge_vector(edge) * (prop.corner_post_width / 2 * (2 - num_convex))
    convex_offset *= 1 if convex_loops[0] else -1
    convex_offset *= 0 if num_convex == 0 else 1

    rail_pos = calc_edge_median(edge) + off + convex_offset
    rail_len = edge.calc_length() - prop.corner_post_width * num_convex
    rail_size = (rail_len, 2 * prop.rail_size, prop.rail_size)
    return rail_pos, rail_size


def array_sloped_rails(bm, min_loc, max_loc, step_size, slope, normal, tangent, rail):
    """ Create an array of sloped rails
    """

    height = rail.corner_post_height - (rail.rail_size / 2)
    tangent_offset = tangent * rail.corner_post_width / 2
    offset = tangent_offset + Vector((0, 0, height - step_size))

    start, end = max_loc + offset, min_loc + offset
    start -= normal * (rail.corner_post_width + rail.rail_size * 0.75)

    rail_count = int((rail.corner_post_height / rail.rail_size) * rail.rail_density)
    step = (height - step_size) / (rail_count + 1)
    for i in range(rail_count + 1):
        add_rail_with_slope(bm, start, end, slope, normal, rail)
        start -= Vector((0, 0, 1)) * step
        end -= Vector((0, 0, 1)) * step


def slope_step_walls(bm, faces, normal, step_size):
    """ Make wall slope along step edges """
    axis = "x" if normal.x else "y"
    func = max if sum(normal) < 0 else min

    for face in faces:
        pos = func([getattr(calc_edge_median(e), axis) for e in face.edges])
        e = [e for e in face.edges if getattr(calc_edge_median(e), axis) == pos].pop()

        for v in e.verts:
            v.co.z += step_size

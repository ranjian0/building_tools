import math
import bmesh
import operator
import functools

from mathutils import Vector, Matrix

from bmesh.types import BMVert, BMEdge, BMFace
from .util_mesh import (
    validate,
    filter_geom,
    edge_vector,
    edge_tangent,
    calc_edge_median,
    calc_verts_median,
)

from .util_material import (
    FaceMap,
    map_new_faces,
    add_facemap_for_groups,
)

from .util_geometry import (
    create_cube_without_faces,
    create_cylinder,
)


class RailingData:
    """ Manage shared railing data/states """

    def __init__(self, prop):
        self.prop = prop
        self.loops = []
        self.loops_edges = []

    def __repr__(self):
        return f"RailingData<{self.prop}>"

    @property
    def loops_colinear(self):
        def is_middle(loop):
            has_next = loop.link_loop_next in self.loops
            has_previous = loop.link_loop_prev in self.loops
            return has_next and has_previous

        return [l for l in self.loops if (is_parallel(l) and is_middle(l))]

    def segments(self, loop):
        angle = loop.calc_angle()
        return polygon_sides_from_angle(round(angle, 4))

    def corner_post_is_cube(self, loop):
        return self.segments(loop) == 4 or self.segments(loop) == math.inf

    def corner_post_is_cylinder(self, loop):
        triangle = self.segments(loop) == 3
        polygon = self.segments(loop) > 4 and self.segments(loop) != math.inf
        return polygon or triangle

    def corner_post_size(self, loop):
        if self.corner_post_is_cylinder(loop):
            val_a = 2 * (self.prop.corner_post_width ** 2)
            val_b = val_a * math.cos(math.pi - loop.calc_angle())
            return math.sqrt(val_a - val_b)
        return self.prop.corner_post_width


def create_railing_from_selection(bm, prop):
    """ create railing from what user has selected
    """
    rail_faces = [f for f in bm.faces if f.select]
    if rail_faces:
        edges = boundary_edges_from_face_selection(bm)
    else:
        edges = [e for e in bm.edges if e.select]
        rail_faces = upward_faces_from_edges(edges)
        rail_faces = list(filter(
            lambda f: sum(int(e in f.edges) for e in edges) > 1, rail_faces)
        )

    create_railing(bm, edges, rail_faces, prop, RailingData(prop))


def create_railing_from_edges(bm, edges, prop):
    """ Create railing along edges
    """
    faces_from_edges = upward_faces_from_edges(edges)
    faces_from_edges = [
        f for f in faces_from_edges if all([e in f.edges for e in edges])
    ]
    create_railing(bm, edges, faces_from_edges, prop, RailingData(prop))


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
    vertices = set(v for e in edges for v in e.verts)
    loops = set(l for v in vertices for l in v.link_loops)
    loops = list(filter(lambda l: l.face in lfaces and l.edge in edges, loops))

    raildata.loops = loops
    raildata.loops_edges = list(filter(lambda l: l.edge in edges, loops))

    create_corner_post(bm, raildata)
    create_fill(bm, raildata)
    bmesh.ops.remove_doubles(bm, verts=bm.verts)


@map_new_faces(FaceMap.RAILING_POSTS)
def create_corner_post(bm, raildata):
    """ Add post at each vert in loops
    """
    prop = raildata.prop
    add_facemap_for_groups(FaceMap.RAILING_POSTS)
    for loop in raildata.loops:
        if prop.remove_colinear and loop in raildata.loops_colinear:
            continue

        v = loop.vert
        e = loop.edge

        vec = loop.calc_tangent()
        width, height = prop.corner_post_width, prop.corner_post_height

        if raildata.corner_post_is_cube(loop):
            off = vec * math.sqrt(2 * ((width / 2) ** 2))
            if is_parallel(loop):
                off = vec * (width / 2)
            pos = v.co + off + Vector((0, 0, height / 2))
            post = add_cube_post(bm, width, height, pos)
        elif raildata.corner_post_is_cylinder(loop):
            pos = v.co + (vec * width) + Vector((0, 0, height / 2))
            post = create_cylinder(bm, width, height, raildata.segments(loop), pos)
            bmesh.ops.rotate(
                bm,
                verts=post["verts"],
                cent=calc_verts_median(post["verts"]),
                matrix=Matrix.Rotation(loop.calc_angle() / 2, 4, "Z"),
            )
        else:
            raise ValueError(f"Invalid Loop data {loop} : angle:{loop.calc_angle()}")

        align_geometry_to_edge(bm, post, e)


def create_fill(bm, raildata):
    """ Create fill types for railing
    """
    prop = raildata.prop
    if prop.fill == "POSTS":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_RAILS))
        create_fill_posts(bm, raildata)
    elif prop.fill == "RAILS":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_RAILS))
        create_fill_rails(bm, raildata)
    elif prop.fill == "WALL":
        add_facemap_for_groups((FaceMap.RAILING_POSTS, FaceMap.RAILING_WALLS))
        create_fill_walls(bm, raildata)


@map_new_faces(FaceMap.RAILING_RAILS)
def create_fill_rails(bm, raildata):
    """ Add rails between corner posts
    """
    prop = raildata.prop
    for loop in raildata.loops_edges:
        edge = loop.edge
        rail_pos, rail_size = calc_rail_position_and_size_for_loop(loop, prop, raildata)

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


@map_new_faces(FaceMap.RAILING_POSTS, skip=FaceMap.RAILING_RAILS)
def create_fill_posts(bm, raildata):
    """ Add posts between corner posts
    """
    prop = raildata.prop
    for loop in raildata.loops_edges:
        edge = loop.edge

        # -- add posts
        add_posts_between_loops(bm, [loop, loop.link_loop_next], prop)
        fill_post_for_colinear_gap(bm, edge, prop, raildata)

        # -- add top rail
        rail_pos, rail_size = calc_rail_position_and_size_for_loop(loop, prop, raildata)
        rail_pos += Vector((0, 0, prop.corner_post_height - prop.rail_size / 2))

        rail = map_new_faces(FaceMap.RAILING_RAILS)(create_cube_without_faces)
        rail = rail(bm, rail_size, rail_pos, left=True, right=True)
        align_geometry_to_edge(bm, rail, edge)


@map_new_faces(FaceMap.RAILING_WALLS)
def create_fill_walls(bm, raildata):
    """ Add walls between corner posts
    """
    prop = raildata.prop
    for loop in raildata.loops_edges:
        edge = loop.edge
        off = raildata.corner_post_size(loop)

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

    n_l = tangent.cross(Vector((0, 0, 1))).to_tuple(2)
    n_r = tangent.cross(Vector((0, 0, -1))).to_tuple(2)

    if "left" in delete_faces:
        faces_to_delete.extend([f for f in faces if f.normal.to_tuple(2) == n_l])
    if "right" in delete_faces:
        faces_to_delete.extend([f for f in faces if f.normal.to_tuple(2) == n_r])

    bmesh.ops.delete(bm, geom=list(set(faces_to_delete)), context="FACES_ONLY")
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
    return list({f for e in edges for f in e.link_faces if f.normal.z})


def create_edge(bm, start, end):
    """ Create and edge between start and end
    """
    start_vert = bm.verts.new(start)
    end_vert = bm.verts.new(end)
    return bm.edges.new((start_vert, end_vert))


def add_cube_post(bm, width, height, position):
    """ Create cube geometry at position
    """
    post = create_cube_without_faces(bm, (width, width, height), position, bottom=True)
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
    pi = round(math.pi, 4)
    if angle == pi:
        return math.inf
    return round((2 * pi) / (pi - angle))


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
    height_v = Vector((0, 0, prop.corner_post_height / 2 - prop.rail_fill.size / 2))
    size = (prop.post_fill.size, prop.post_fill.size, prop.corner_post_height - prop.rail_fill.size)
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
    post_count = round((length / prop.post_fill.size) * prop.post_fill.density)
    array_elements(bm, post, post_count, start, stop)


def fill_post_for_colinear_gap(bm, edge, prop, raildata):
    """ Add a post where corner posts were removed due to belonging to co-linear loops
    """
    off = edge_tangent(edge).normalized() * (prop.corner_post_width / 2)
    height_v = Vector((0, 0, prop.corner_post_height / 2 - prop.rail_size / 2))
    size = (prop.post_size, prop.post_size, prop.corner_post_height - prop.rail_size)
    if prop.remove_colinear:
        for loop in raildata.loops_colinear:
            if loop.edge == edge or loop.link_loop_prev.edge == edge:
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
        min_location, max_location = min_max_vert_locations(
            [vert for edge in group for vert in edge.verts]
        )
        step_size = abs((max_location.z - min_location.z) / (prop.step_count - 1))
        min_location.z += step_size

        #  -- slope and edge tangent
        slope = slope_between_vectors(max_location, min_location)
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
        tangent = edge_tangent(group[-1]).normalized()
        min_location, max_location = min_max_vert_locations(
            [vert for edge in group for vert in edge.verts]
        )

        step_size = (max_location.z - min_location.z) / (prop.step_count - 1)
        max_location.z += step_size

        #  -- add corner post at max location
        add_corner_post_for_last_fill_rail_step(
            bm, max_location, step_size, tangent, normal, prop
        )

        #  -- add corner post at min location if there is no landing
        if not prop.landing:
            add_corner_post_for_start_fill_rail_step(
                bm, min_location, step_size, tangent, normal, prop
            )
            min_location += normal * rail.corner_post_width

        slope = slope_between_vectors(max_location, min_location)
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
        min_location, max_location = min_max_vert_locations(
            [vert for edge in group for vert in edge.verts]
        )
        step_size = abs((max_location.z - min_location.z) / (prop.step_count - 1))

        for edge in group:
            tan = edge_tangent(edge)
            start, end = [v.co for v in edge.verts]
            wall = create_wall(
                bm, start, end, rail.corner_post_height, rail.wall_width, tan
            )
            inner = "right" if normal.cross(tan).z > 0.0 else "left"
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


def slope_between_vectors(start, end):
    """ Calculate the slope between start and end
    """
    change = start - end
    return change.z / change.xy.length


def min_max_vert_locations(verts):
    """ Find the minimum and maximum location in verts based on normal direction
    """
    locations = [vert.co.copy() for vert in verts]
    return sorted(locations, key=lambda c: c.length)[:: len(locations) - 1]


def add_posts_along_edge_with_slope(bm, edge, slope, normal, tangent, prop):
    """
    Add posts along an edge with increasing height based on slope
    """
    post_count = round((edge.calc_length() / prop.post_size) * prop.post_density)
    post_spacing = edge.calc_length() / post_count
    post_height = prop.corner_post_height - (prop.rail_size / 2)

    tan_offset = tangent * prop.corner_post_width / 2
    post_offset = tan_offset + (-normal * prop.post_size / 2)

    end, start = min_max_vert_locations(edge.verts)
    for i in range(post_count):
        height = post_height + abs(slope * (i * post_spacing))
        position = start + post_offset - (normal * (i * post_spacing))
        position += Vector((0, 0, height / 2))
        size = (prop.post_size,) * 2 + (height,)
        post = create_cube_without_faces(bm, size, position, top=True, bottom=True)
        bmesh.ops.rotate(
            bm,
            verts=post["verts"],
            cent=calc_verts_median(post["verts"]),
            matrix=Matrix.Rotation(math.atan2(normal.y, normal.x), 4, "Z"),
        )


@map_new_faces(FaceMap.RAILING_RAILS)
def add_rail_with_slope(bm, start, end, slope, normal, prop):
    """ Add a rail from start to end with a given slope
    """
    length = (start - end).length + prop.rail_size
    size = (length, 2 * prop.rail_size, prop.rail_size)
    position = start.lerp(end, 0.5) - ((end - start).normalized() * prop.rail_size / 2)

    rail = create_cube_without_faces(bm, size, position, right=True)
    bmesh.ops.rotate(
        bm,
        verts=rail["verts"],
        cent=calc_verts_median(rail["verts"]),
        matrix=Matrix.Rotation(math.atan2(normal.y, normal.x), 4, "Z"),
    )

    bmesh.ops.rotate(
        bm,
        verts=rail["verts"],
        cent=calc_verts_median(rail["verts"]),
        matrix=Matrix.Rotation(math.atan(slope), 4, normal.cross(Vector((0, 0, 1)))),
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


def calc_rail_position_and_size_for_loop(loop, prop, raildata=None):
    """ Calculate proper position and size for a rail along the loop's edge
    """
    edge = loop.edge
    off = edge_tangent(edge).normalized() * (prop.corner_post_width / 2)
    convex_loops = [l.is_convex for l in (loop, loop.link_loop_next)]
    num_convex = sum(convex_loops)
    convex_offset = edge_vector(edge) * (prop.corner_post_width / 2 * (2 - num_convex))
    convex_offset *= 1 if convex_loops[0] else -1
    convex_offset *= 0 if num_convex == 0 else 1

    rail_pos = calc_edge_median(edge) + off + convex_offset
    # rail_len = edge.calc_length() - raildata.corner_post_size(loop) * num_convex
    rail_len = edge.calc_length() - prop.corner_post_width * num_convex
    if raildata and not prop.remove_colinear:
        is_colinear = (
            loop in raildata.loops_colinear,
            loop.link_loop_next in raildata.loops_colinear,
        )
        if any(is_colinear):
            rail_len -= prop.corner_post_width / 2
            colinear_offset = edge_vector(edge) * (prop.corner_post_width / 4)
            if is_colinear[0]:
                rail_pos += colinear_offset
            if is_colinear[1]:
                rail_pos -= colinear_offset

        if all(is_colinear):
            rail_len -= prop.corner_post_width / 2

    rail_size = (rail_len, 2 * prop.rail_fill.size, prop.rail_fill.size)
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
    """ Make wall slope along step edges
    """
    for face in faces:
        loc = min([calc_edge_median(e).xy.length for e in face.edges])
        e = [e for e in face.edges if calc_edge_median(e).xy.length == loc].pop()

        for v in e.verts:
            v.co.z += step_size


def add_corner_post_for_last_fill_rail_step(bm, loc, step_size, tan, normal, prop):
    """ Add a corner posts at the bottom of stairs when fill is rails
    """

    rail = prop.rail
    tangent_offset = tan * rail.corner_post_width / 2
    post_w, post_h = rail.corner_post_width, rail.corner_post_height
    post_pos = loc + Vector((0, 0, post_h / 2 - step_size))
    post_pos += tangent_offset + (normal * -post_w / 2)
    if not prop.landing:
        post_pos += Vector((0, 0, rail.rail_size / 4))
        post_h += rail.rail_size / 2

    post = map_new_faces(FaceMap.RAILING_POSTS)(add_cube_post)
    post = post(bm, post_w, post_h, post_pos)
    bmesh.ops.rotate(
        bm,
        verts=post["verts"],
        cent=calc_verts_median(post["verts"]),
        matrix=Matrix.Rotation(math.atan2(normal.y, normal.x), 4, "Z"),
    )


def add_corner_post_for_start_fill_rail_step(bm, loc, step_size, tan, normal, prop):
    """ Add a corner posts at the beginning of stairs when fill is rails
    """

    rail = prop.rail
    tangent_offset = tan * rail.corner_post_width / 2
    post_w, post_h = rail.corner_post_width, rail.corner_post_height
    post_pos = loc + Vector((0, 0, post_h / 2))
    post_pos += tangent_offset + (normal * post_w / 2)
    post_pos += Vector((0, 0, rail.rail_size / 2))
    post_h += rail.rail_size

    post = map_new_faces(FaceMap.RAILING_POSTS)(add_cube_post)
    post = post(bm, post_w, post_h, post_pos)
    bmesh.ops.rotate(
        bm,
        verts=post["verts"],
        cent=calc_verts_median(post["verts"]),
        matrix=Matrix.Rotation(math.atan2(normal.y, normal.x), 4, "Z"),
    )

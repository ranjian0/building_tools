import functools as ft
import math
import operator

import bmesh
import bpy
from bmesh.types import BMVert, BMEdge, BMFace

from .util_common import local_xyz, equal
from .util_constants import VEC_UP, VEC_DOWN


def get_edit_mesh():
    """ Get editmode mesh
    """
    return bpy.context.edit_object.data


def create_mesh(name):
    """ Make new mesh data
    """
    return bpy.data.meshes.new(name)


def select(elements, val=True):
    """ For each item in elements set select to val
    """
    for el in elements:
        el.select_set(val)


def validate(elements):
    """ Return only valid items in elements
    """
    return list(filter(lambda el: el.is_valid, elements))


def filter_geom(geom, _type):
    """ Find all elements of type _type in geom iterable
    """
    return list(filter(lambda x: isinstance(x, _type), geom))


def edge_tangent(edge):
    """ Find the tangent of an edge
    """
    tan = None
    for l in edge.link_loops:
        t = edge.calc_tangent(l)
        if not round(t.z):
            tan = t
    return tan


def edge_vector(edge):
    """ Return the normalized vector between edge vertices
    """
    v1, v2 = edge.verts
    return (v2.co - v1.co).normalized()


def edge_slope(e):
    """ Calculate the slope of an edge, 'inf' for vertical edges
    """
    v = edge_vector(e)
    try:
        return v.z / round(v.xy.length, 4)
    except ZeroDivisionError:
        return float("inf")


def edge_angle(e):
    """ Calculate the angle an edge makes with horizontal axis
    """
    return math.atan(edge_slope(e))


def edge_is_vertical(e):
    """ Check if edge is vertical (infinite slope)
    """
    return edge_slope(e) == float("inf")


def edge_is_horizontal(e):
    """ Check if edge is horizontal (zero slope)
    """
    return round(edge_slope(e), 2) == 0.0


def edge_is_sloped(e):
    """ Check if edge slope is between vertical and horizontal axis
    """
    sl = edge_slope(e)
    return sl > float("-inf") and sl < float("inf") and sl != 0.0


def valid_ngon(face):
    """ faces with rectangular shape and undivided horizontal edges are valid
    """
    horizontal_edges = filter_horizontal_edges(face.edges)
    return len(horizontal_edges) == 2 and is_rectangle(face)


def is_rectangle(face):
    """ check if face is rectangular
    """
    angles = [math.pi - l.calc_angle() for l in face.loops]
    right_angles = len([a for a in angles if math.pi/2-0.001 < a < math.pi/2+0.001])
    straight_angles = len([a for a in angles if -0.001 < a < 0.001])
    return right_angles == 4 and straight_angles == len(angles) - 4


def vec_equal(a, b):
    angle = a.angle(b)
    return angle < 0.001 and angle > -0.001


def vec_opposite(a, b):
    angle = a.angle(b)
    return angle < math.pi + 0.001 and angle > math.pi - 0.001


def is_parallel(a, b):
    return vec_equal(a, b) or vec_opposite(a, b)


def sort_edges_clockwise(edges):
    """ sort edges clockwise based on angle from their median center
    """
    median_reference = ft.reduce(operator.add, map(calc_edge_median, edges)) / len(
        edges
    )

    def sort_function(edge):
        vector_difference = median_reference - calc_edge_median(edge)
        return math.atan2(vector_difference.y, vector_difference.x)

    return sorted(edges, key=sort_function, reverse=True)


def filter_vertical_edges(edges):
    """ Determine edges that are vertical
    In 2D space(XY Plane), vertical is Y-axis, In 3D, vertical is Z-axis
    """
    rnd = ft.partial(round, ndigits=3)
    space_2d = len(set(rnd(v.co.z) for e in edges for v in e.verts)) == 1
    if space_2d:
        return list(filter(lambda e: abs(rnd(edge_vector(e).y)) == 1.0, edges))

    # Any edge that has upward vector is considered vertical
    # if the edge is slanting, it must be slanting on only one axis
    def vertical_3d(e):
        vec = edge_vector(e)
        straight = rnd(vec.z) and not rnd(vec.x) and not rnd(vec.y)
        slanted_x = rnd(vec.z) and rnd(vec.x) and not rnd(vec.y)
        slanted_y = rnd(vec.z) and not rnd(vec.x) and rnd(vec.y)
        return straight or slanted_x or slanted_y
    return list(filter(lambda e: vertical_3d(e), edges))


def filter_horizontal_edges(edges):
    """ Determine edges that are horizontal
    In 2D space(XY Plane), horizontal is X-axis, In 3D, horizontal is XY-plane
    """
    rnd = ft.partial(round, ndigits=3)
    space_2d = len(set(rnd(v.co.z) for e in edges for v in e.verts)) == 1
    if space_2d:
        return list(filter(lambda e: abs(rnd(edge_vector(e).x)) == 1.0, edges))

    # Any edge that is at right angle to global up vector is horizontal
    def horizontal_3d(e):
        vec = edge_vector(e)
        if rnd(vec.length) <= 0.0:
            return False
        return rnd(vec.angle(VEC_UP)) == rnd(math.pi / 2)
    return list(filter(lambda e: horizontal_3d(e), edges))


def filter_parallel_edges(edges, dir):
    """ Determine edges that are parallel to a vector
    """
    return [e for e in edges if is_parallel(edge_vector(e), dir)]


def calc_edge_median(edge):
    """ Calculate the center position of edge
    """
    return calc_verts_median(edge.verts)


def calc_verts_median(verts):
    """ Determine the median position of verts
    """
    return ft.reduce(operator.add, [v.co for v in verts]) / len(verts)


def calc_face_dimensions(face):
    """ Determine the width and height of face
    """
    horizontal_edges = filter_horizontal_edges(face.edges)
    vertical_edges = filter_vertical_edges(face.edges)
    width = sum(e.calc_length() for e in horizontal_edges) / 2
    height = sum(e.calc_length() for e in vertical_edges) / 2
    return round(width, 4), round(height, 4)


def face_with_verts(bm, verts, default=None):
    """ Find a face in the bmesh with the given verts
    """
    for face in bm.faces:
        equal = map(
            operator.eq,
            sorted(verts, key=operator.attrgetter("index")),
            sorted(face.verts, key=operator.attrgetter("index")),
        )
        if len(face.verts) == len(verts) and all(equal):
            return face
    return default


def subdivide_face_horizontally(bm, face, widths):
    """ Subdivide the face horizontally, widths from left to right (face x axis)
    """
    if len(widths) < 2:
        return [face]
    edges = filter_horizontal_edges(face.edges)
    direction, _, _ = local_xyz(face)
    inner_edges = subdivide_edges(bm, edges, direction, widths)
    return sort_faces(list({f for e in inner_edges for f in e.link_faces}), direction)


def subdivide_face_vertically(bm, face, widths):
    """ Subdivide the face vertically, widths from bottom to top (face y axis)
    """
    if len(widths) < 2:
        return [face]
    edges = filter_vertical_edges(face.edges)
    _, direction, _ = local_xyz(face)
    inner_edges = subdivide_edges(bm, edges, direction, widths)
    return sort_faces(list({f for e in inner_edges for f in e.link_faces}), direction)


def subdivide_edges(bm, edges, direction, widths):
    """ Subdivide edges in a direction, widths in the direction
    """
    dir = direction.copy().normalized()
    cuts = len(widths) - 1
    res = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts)
    inner_edges = filter_geom(res.get("geom_inner"), BMEdge)
    distance = sum(widths) / len(widths)
    final_position = 0.0
    for i, edge in enumerate(sort_edges(inner_edges, dir)):
        original_position = (i + 1) * distance
        final_position += widths[i]
        diff = final_position - original_position
        bmesh.ops.translate(bm, verts=edge.verts, vec=diff * dir)
    return inner_edges


def arc_edge(bm, edge, resolution, height, xyz, function="SPHERE"):
    """ Subdivide the given edge and offset vertices to form an arc
    """
    length = edge.calc_length()
    median = calc_edge_median(edge)
    orient = xyz[0] if edge_is_horizontal(edge) else xyz[1]
    arc_direction = xyz[1] if edge_is_horizontal(edge) else xyz[0]
    ret = bmesh.ops.subdivide_edges(bm, edges=[edge], cuts=resolution)

    verts = sort_verts(
        list({v for e in filter_geom(ret["geom_split"], bmesh.types.BMEdge) for v in e.verts}),
        orient
    )
    theta = math.pi / (len(verts) - 1)
    orient *= (1 / orient.length)
    arc_direction.normalize()

    def arc_sine(verts):
        for idx, v in enumerate(verts):
            v.co += arc_direction * math.sin(theta * idx) * height

    def arc_sphere(verts):
        for idx, v in enumerate(verts):
            angle = math.pi - (theta * idx)
            v.co = median + orient * math.cos(angle) * length / 2
            v.co += arc_direction * math.sin(angle) * height

    {"SINE": arc_sine, "SPHERE": arc_sphere}.get(function)(verts)
    return ret


def extrude_face(bm, face, extrude_depth):
    """extrude a face
    """
    extruded_face = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces")[0]
    bmesh.ops.translate(bm, verts=extruded_face.verts, vec=extruded_face.normal * extrude_depth)
    surrounding_faces = list({f for edge in extruded_face.edges for f in edge.link_faces if f not in [extruded_face]})
    return extruded_face, surrounding_faces


def extrude_face_region(bm, faces, depth, normal):
    """extrude a face and delete redundant faces
    """
    initial_locations = [f.calc_center_bounds() for f in faces]
    geom = bmesh.ops.extrude_face_region(bm, geom=faces).get("geom")
    verts = filter_geom(geom, BMVert)
    bmesh.ops.translate(bm, verts=verts, vec=normal * depth)

    bmesh.ops.delete(bm, geom=faces, context="FACES")  # remove redundant faces

    extruded_faces = filter_geom(geom, BMFace)
    # order extruded faces as per initially passed
    final_locations = [loc + depth * normal for loc in initial_locations]
    extruded_faces = closest_faces(extruded_faces, final_locations)
    surrounding_faces = list({f for edge in filter_geom(geom, BMEdge) for f in edge.link_faces if f not in extruded_faces})
    return extruded_faces, surrounding_faces


def closest_faces(faces, locations):
    def get_face(faces, location):
        for f in faces:
            if equal((f.calc_center_bounds() - location).length, 0):
                return f

    return [get_face(faces, l) for l in locations]


def get_selected_face_dimensions(context):
    """ Get dimensions of selected face
    """
    bm = bmesh.from_edit_mesh(context.edit_object.data)
    wall = [f for f in bm.faces if f.select]
    if wall:
        return calc_face_dimensions(wall[0])
    return 1, 1


def create_face(bm, size, offset, xyz):
    """ Create a face in xy plane of xyz space
    """
    offset = offset.x * xyz[0] + offset.y * xyz[1]

    v1 = bmesh.ops.create_vert(bm, co=offset+size.x*xyz[0]/2+size.y*xyz[1]/2)["vert"][0]
    v2 = bmesh.ops.create_vert(bm, co=offset+size.x*xyz[0]/2-size.y*xyz[1]/2)["vert"][0]
    v3 = bmesh.ops.create_vert(bm, co=offset-size.x*xyz[0]/2+size.y*xyz[1]/2)["vert"][0]
    v4 = bmesh.ops.create_vert(bm, co=offset-size.x*xyz[0]/2-size.y*xyz[1]/2)["vert"][0]

    return bmesh.ops.contextual_create(bm, geom=[v1, v2, v3, v4])["faces"][0]


def get_top_edges(edges, n=1):
    return sort_edges(edges, VEC_DOWN)[:n]


def get_bottom_edges(edges, n=1):
    return sort_edges(edges, VEC_UP)[:n]


def get_top_faces(faces, n=1):
    return sort_faces(faces, VEC_DOWN)[:n]


def get_bottom_faces(faces, n=1):
    return sort_faces(faces, VEC_UP)[:n]


def sort_faces(faces, direction):
    return sorted(faces, key=lambda f: direction.dot(f.calc_center_median()))


def sort_edges(edges, direction):
    return sorted(edges, key=lambda e: direction.dot(calc_edge_median(e)))


def sort_verts(verts, direction):
    return sorted(verts, key=lambda v: direction.dot(v.co))


def ngon_to_quad(bm, face):
    """ Try to convert rectangular ngon to quad
    Method:
    - Perform inset.
    - Dissolve all edges that are created from lone(non-corner) verts.
    - Dissolve all the lone(non-corner) verts.
    """

    INSET_EPS = 0.0011
    bmesh.ops.inset_individual(
        bm, faces=[face], thickness=INSET_EPS, use_even_offset=True
    )

    diss_verts = list({loop.vert for loop in face.loops if equal(loop.calc_angle(), math.pi)})
    diss_edges = list({e for v in diss_verts for e in v.link_edges if e not in face.edges})
    bmesh.ops.dissolve_edges(bm, edges=diss_edges)
    bmesh.ops.dissolve_verts(bm, verts=diss_verts)

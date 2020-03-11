import bpy
import math
import bmesh
import operator
import functools as ft
from mathutils import Matrix, Vector
from bmesh.types import BMVert


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


def filter_vertical_edges(edges, normal):
    """ Determine edges that are vertical based on a normal value
    """
    res = []
    rnd = ft.partial(round, ndigits=3)

    for e in edges:
        if rnd(normal.x):
            s = set([rnd(v.co.y) for v in e.verts])
        else:
            s = set([rnd(v.co.x) for v in e.verts])

        if len(s) == 1:
            res.append(e)
    return res


def filter_horizontal_edges(edges, normal):
    """ Determine edges that are horizontal based on a normal value
    """
    res = []
    rnd = ft.partial(round, ndigits=3)

    for e in edges:
        if rnd(normal.z):
            s = set([rnd(v.co.y) for v in e.verts])
        else:
            s = set([rnd(v.co.z) for v in e.verts])

        if len(s) == 1:
            res.append(e)
    return res


def calc_edge_median(edge):
    """ Calculate the center position of edge
    """
    return ft.reduce(operator.add, [v.co for v in edge.verts]) / len(edge.verts)


def calc_verts_median(verts):
    """ Determine the median position of verts
    """
    return ft.reduce(operator.add, [v.co for v in verts]) / len(verts)


def calc_face_dimensions(face):
    """ Determine the width and height of face
    """
    vertical = filter_vertical_edges(face.edges, face.normal).pop()
    horizontal = filter_horizontal_edges(face.edges, face.normal).pop()
    return horizontal.calc_length(), vertical.calc_length()


def face_with_verts(bm, verts, default=None):
    """ Find a face in the bmesh with the given verts
    """
    for face in bm.faces:
        equal = map(
            operator.eq,
            sorted(verts, key=operator.attrgetter('index')),
            sorted(face.verts, key=operator.attrgetter('index')),
        )
        if len(face.verts) == len(verts) and all(equal):
            return face
    return default


def subdivide_face_edges_vertical(bm, face, cuts=4):
    """ Subdivide the vertical edges of a face
    """
    e = filter_horizontal_edges(face.edges, face.normal)
    return bmesh.ops.subdivide_edges(bm, edges=e, cuts=cuts)


def subdivide_face_edges_horizontal(bm, face, cuts=4):
    """ Subdivide the horizontal edges of a face
    """
    e = filter_vertical_edges(face.edges, face.normal)
    return bmesh.ops.subdivide_edges(bm, edges=e, cuts=cuts)


def inset_face_with_scale_offset(bm, face, scale_y, scale_x, offx=0, offy=0, offz=0):
    """ Inset a face using right angled cuts, then offset and scale inner face
    """
    cuts = 2
    scale = cuts + 1
    scale_y *= scale
    scale_x *= scale

    do_vertical = scale_y < scale
    do_horizontal = scale_x < scale

    if not do_horizontal and not do_vertical:
        return face

    face.select = False
    verts = subdivide_flagged_edges(
        bm, face, do_horizontal, do_vertical, scale_x, scale_y
    )
    offset_flagged_verts(bm, verts, do_horizontal, do_vertical, offx, offy, offz)
    return face_with_verts(bm, verts)


def subdivide_flagged_edges(bm, face, cut_horizontal, cut_vertical, scale_x, scale_y):
    """ Subdivide the edges of a face that are flagged
    """
    normal = face.normal
    median = face.calc_center_median()
    if cut_horizontal:
        horizontal = filter_horizontal_edges(face.edges, normal)
        verts = subdivide_edges_and_scale_inner(
            bm, horizontal, (scale_x, scale_x, 1), median
        )

    if cut_vertical:
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts))
        face = face_with_verts(bm, verts) if cut_horizontal else face
        vertical = filter_vertical_edges(face.edges, normal)
        verts = subdivide_edges_and_scale_inner(bm, vertical, (1, 1, scale_y), median)
    return verts


def offset_flagged_verts(bm, verts, horizontal, vertical, offx, offy, offz):
    """ Move the flagged vertices
    """
    if horizontal and vertical:
        link_edges = [e for v in verts for e in v.link_edges]
        all_verts = list({v for e in link_edges for v in e.verts})
        bmesh.ops.translate(bm, verts=all_verts, vec=(offx, offy, 0))
    elif horizontal and not vertical:
        bmesh.ops.translate(bm, verts=verts, vec=(offx, offy, 0))
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, offz))


def subdivide_edges_and_scale_inner(bm, edges, scale, scale_center):
    """ subdivide the edges twice and scale the middle section
    """
    sp_res = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=2)
    verts = filter_geom(sp_res["geom_inner"], BMVert)
    bmesh.ops.scale(bm, vec=scale, verts=verts, space=Matrix.Translation(-scale_center))
    return verts


def edge_split_offset(bm, edges, verts, offset, connect_verts=False):
    """ Split the edges, offset amount from verts
    """
    new_verts = []
    for idx, e in enumerate(edges):
        vert = verts[idx]
        _, v = bmesh.utils.edge_split(e, vert, offset / e.calc_length())
        new_verts.append(v)

    if connect_verts:
        res = bmesh.ops.connect_verts(bm, verts=new_verts).get("edges")
        return res
    return new_verts


def arc_edge(bm, edge, resolution, height, offset, function="SPHERE"):
    """ Subdivide the given edge and offset vertices to form an arc
    """
    length = edge.calc_length()
    median = calc_edge_median(edge)
    normal = edge_vector(edge).cross(Vector((0, 0, 1)))

    ret = bmesh.ops.subdivide_edges(bm, edges=[edge], cuts=resolution)
    verts = list(
        {v for e in filter_geom(ret["geom_split"], bmesh.types.BMEdge) for v in e.verts}
    )
    verts.sort(key=lambda v: v.co.x if normal.y else v.co.y)
    theta = math.pi / (len(verts) - 1)

    def arc_sine(verts):
        for idx, v in enumerate(verts):
            v.co.z -= offset
            v.co.z += math.sin(theta * idx) * height

    def arc_sphere(verts):
        for idx, v in enumerate(verts):
            angle = math.pi - (theta * idx)
            v.co.z -= offset
            v.co.z += math.sin(angle) * height
            if normal.y:
                v.co.x = median.x + math.cos(angle) * length / 2
            else:
                v.co.y = median.y + math.cos(angle) * length / 2

    {"SINE": arc_sine, "SPHERE": arc_sphere}.get(function)(verts)
    return ret


def extrude_face_and_delete_bottom(bm, face, extrude_depth):
    """extrude a face and delete bottom face from new geometry
    """
    f = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces").pop()
    bmesh.ops.translate(bm, verts=f.verts, vec=f.normal * extrude_depth)
    bottom_edge = min(
        filter_horizontal_edges(face.edges, face.normal),
        key=lambda e: calc_edge_median(e).z,
    )
    hidden = min(bottom_edge.link_faces, key=lambda f: f.calc_center_median().z)
    bmesh.ops.delete(bm, geom=[hidden], context="FACES")
    return f


def move_slab_splitface_to_wall(bm, face):
    """ Align a face that was split from a slab to building wall
    """
    if not face_belongs_to_slab(bm, face):
        return face

    slab_outset = bpy.context.object.tracked_properties.slab_outset
    target_edges = filter_horizontal_edges(face.edges, face.normal.copy())
    sort_axis = "x" if face.normal.x else "y"

    new_verts = []
    target_faces = [face]
    for edge in target_edges:
        other_face = (set(edge.link_faces) - {face}).pop()
        func = min if getattr(face.normal, sort_axis) > 0 else max
        other_edge = func(
            other_face.edges, key=lambda e: getattr(calc_edge_median(e), sort_axis)
        )

        verts, faces = cut_edge_based_on_other_edge(
            bm, edge, other_edge, (-face.normal * slab_outset)
        )
        new_verts.extend(verts)
        target_faces.extend(faces)

    bmesh.ops.delete(bm, geom=target_faces, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=target_edges, context="EDGES")
    ret = bmesh.ops.contextual_create(bm, geom=new_verts)
    return ret.get("faces").pop()


def face_belongs_to_slab(bm, face):
    """ Check if face belongs to generate slab faces that dont face upwards
    """

    if face.normal.z:
        return False

    slab_outset = bpy.context.object.tracked_properties.slab_outset
    if slab_outset <= 0.00001:
        return False

    slab_facemap = bpy.context.object.face_maps.get("slabs")
    if not slab_facemap:
        return False

    active_face_map = bm.faces.layers.face_map.active
    if face[active_face_map] != slab_facemap.index:
        return False

    return True


def cut_edge_based_on_other_edge(bm, edge, other_edge, cut_direction):
    """ Project cuts onto other_edge based on edge.verts and cut_direction
    """
    new_edges = []
    new_verts = []
    target_faces = []
    for v in edge.verts:
        split_point = v.co + cut_direction
        e, new_vert = split_edge_at_point_from_closest_vert(other_edge, v, split_point)
        e = bmesh.ops.connect_vert_pair(bm, verts=[v, new_vert]).get("edges").pop()
        new_edges.append(e)
        new_verts.append(new_vert)

    target_faces.append(
        (set(new_edges[0].link_faces) & set(new_edges[1].link_faces)).pop()
    )

    return new_verts, target_faces


def split_edge_at_point_from_closest_vert(edge, vert, split_point):
    """ Split the edge 'edge' from one of its vertices that is closest to
        'vert' at the split_point
    """
    close_vert = min(edge.verts, key=lambda ov: (ov.co - vert.co).length)
    split_length = (close_vert.co - split_point).length
    split_factor = split_length / edge.calc_length()
    return bmesh.utils.edge_split(edge, close_vert, split_factor)

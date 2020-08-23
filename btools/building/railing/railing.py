import math
from collections import namedtuple

import bmesh
from bmesh.types import BMFace, BMEdge, BMVert
from mathutils import Vector, Matrix, Quaternion

from ...utils import (
    clamp,
    FaceMap,
    VEC_DOWN,
    validate,
    sort_edges,
    sort_verts,
    edge_vector,
    filter_geom,
    map_new_faces,
    edge_is_sloped,
    edge_is_vertical,
    subdivide_edges,
    calc_verts_median,
    add_facemap_for_groups,
)

RailingResult = namedtuple("RailingResult", "corner_posts top_rails fill")


def create_railing(bm, faces, prop, normal):
    vertical_edges = list({e for f in faces for e in f.edges if edge_is_vertical(e)})
    add_facemap_for_groups(FaceMap.RAILING_POSTS)
    cposts = make_corner_posts(bm, vertical_edges, prop, faces[0].normal)
    top_rails, fills = [], []
    for f in faces:
        top_rail, fill = make_fill(bm, f, prop)
        fills.append(fill)
        top_rails.append(top_rail)
    bmesh.ops.delete(bm, geom=faces, context="FACES")  # delete reference faces
    return RailingResult(cposts, top_rails, fills)


@map_new_faces(FaceMap.RAILING_POSTS)
def make_corner_posts(bm, edges, prop, up):
    posts = []
    for edge in edges:
        ret = bmesh.ops.duplicate(bm, geom=[edge])
        dup_edge = filter_geom(ret["geom"], BMEdge)[0]
        post = edge_to_cylinder(bm, dup_edge, prop.corner_post_width / 2, up, fill=True)
        posts.append(list({f for v in post for f in v.link_faces}))
    return posts


def make_fill(bm, face, prop):
    # duplicate original face and resize
    ret = bmesh.ops.duplicate(bm, geom=[face])
    dup_face = filter_geom(ret["geom"], BMFace)[0]
    non_vertical = [e for e in dup_face.edges if not edge_is_vertical(e)]
    top_edge = sort_edges(non_vertical, Vector((0., 0., -1.)))[0]
    bot_edge = sort_edges(non_vertical, Vector((0., 0., -1.)))[-1]
    bmesh.ops.translate(bm, verts=top_edge.verts, vec=Vector((0., 0., -1.))*prop.corner_post_width/2)

    # make dupface fit flush between corner posts
    translate_bounds(bm, dup_face.verts, edge_vector(top_edge), prop.corner_post_width/2)

    # create railing top
    add_facemap_for_groups(FaceMap.RAILING_RAILS)
    top_rail = create_railing_top(bm, top_edge, prop)

    # create fill
    if prop.fill == "POSTS":
        if prop.bottom_rail:
            create_railing_bottom(bm, bot_edge, prop)
        fill = create_fill_posts(bm, dup_face, prop)
    elif prop.fill == "RAILS":
        fill = create_fill_rails(bm, dup_face, prop)
    elif prop.fill == "WALL":
        add_facemap_for_groups(FaceMap.RAILING_WALLS)
        if prop.bottom_rail:
            create_railing_bottom(bm, bot_edge, prop)
        fill = create_fill_walls(bm, dup_face, prop)

    return top_rail, fill


@map_new_faces(FaceMap.RAILING_RAILS)
def create_railing_top(bm, top_edge, prop):
    cylinder = create_railing_cylinder(bm, top_edge, prop)
    bmesh.ops.translate(bm, verts=top_edge.verts, vec=(0., 0., -prop.corner_post_width/2))
    return list({f for v in cylinder for f in v.link_faces})


@map_new_faces(FaceMap.RAILING_RAILS)
def create_railing_bottom(bm, bot_edge, prop):
    initial_loc = prop.corner_post_width * 1.5
    clamped_offset = clamp(
        prop.bottom_rail_offset,
        -initial_loc + prop.corner_post_width / 2,
        prop.corner_post_height - initial_loc * 2)
    bmesh.ops.translate(bm, verts=bot_edge.verts, vec=(0, 0, initial_loc + clamped_offset))
    create_railing_cylinder(bm, bot_edge, prop)
    bmesh.ops.translate(bm, verts=bot_edge.verts, vec=(0, 0, prop.corner_post_width/2))


def create_railing_cylinder(bm, edge, prop):
    ret = bmesh.ops.duplicate(bm, geom=[edge])
    top_dup_edge = filter_geom(ret["geom"], BMEdge)[0]
    vec = edge_vector(top_dup_edge)

    up = vec.copy()
    horizon = vec.cross(Vector((0., 0., 1.)))
    up.rotate(Quaternion(horizon, math.pi/2).to_euler())

    sloped = edge_is_sloped(top_dup_edge)
    cylinder = edge_to_cylinder(bm, top_dup_edge, prop.corner_post_width/2, up)
    if sloped:
        rotate_sloped_rail_bounds(bm, cylinder, vec)
    return cylinder


@map_new_faces(FaceMap.RAILING_POSTS)
def create_fill_posts(bm, face, prop):
    result = []
    sorted_edges = sort_edges(
        [e for e in face.edges if not edge_is_vertical(e)], Vector((0.0, 0.0, -1.0))
    )

    # create posts
    post_size = min(prop.post_fill.size, prop.corner_post_width)

    top_edge, bottom_edge = sorted_edges[0], sorted_edges[-1]
    top_edge_vector = top_edge.verts[0].co - top_edge.verts[1].co
    n_posts = round(top_edge_vector.length * prop.post_fill.density / post_size)
    dir = edge_vector(top_edge)
    sloped = edge_is_sloped(top_edge)
    if n_posts != 0:
        inner_edges = subdivide_edges(
            bm, [top_edge, bottom_edge], dir, widths=[1.0] * (n_posts + 1)
        )
        for edge in inner_edges:
            ret = bmesh.ops.duplicate(bm, geom=[edge])
            dup_edge = filter_geom(ret["geom"], BMEdge)[0]
            up = face.normal
            vec = edge_vector(dup_edge)
            cylinder = edge_to_cylinder(bm, dup_edge, post_size/2, up)
            if sloped:
                rotate_faces(bm, cylinder, vec, dir, prop)
            result.append(list({f for v in cylinder for f in v.link_faces}))
        # delete reference faces
        bmesh.ops.delete(
            bm, geom=list({f for e in inner_edges for f in e.link_faces}), context="FACES"
        )
    else:
        # delete reference faces
        bmesh.ops.delete(bm, geom=[face], context="FACES")
    return result


@map_new_faces(FaceMap.RAILING_RAILS)
def create_fill_rails(bm, face, prop):
    # create rails
    result = []
    rail_size = min(prop.rail_fill.size, prop.corner_post_width)

    vertical_edges = [e for e in face.edges if edge_is_vertical(e)]
    n_rails = math.floor(
        vertical_edges[0].calc_length() * prop.rail_fill.density / rail_size
    )
    if n_rails != 0:
        inner_edges = subdivide_edges(
            bm, vertical_edges, Vector((0.0, 0.0, 1.0)), widths=[1.0] * (n_rails + 1)
        )
        for edge in inner_edges:
            ret = bmesh.ops.duplicate(bm, geom=[edge])
            dup_edge = filter_geom(ret["geom"], BMEdge)[0]
            up = face.normal

            vec = edge_vector(dup_edge)
            sloped = edge_is_sloped(dup_edge)
            cylinder = edge_to_cylinder(bm, dup_edge, rail_size / 2, up)
            if sloped:
                rotate_sloped_rail_bounds(bm, cylinder, vec)

        # delete reference faces
        dup_faces = list({f for e in inner_edges for f in e.link_faces})
        bmesh.ops.delete(bm, geom=dup_faces, context="FACES")
        result.append(list({f for v in cylinder for f in v.link_faces}))
    else:
        # delete reference faces
        bmesh.ops.delete(bm, geom=[face], context="FACES")
    return result


@map_new_faces(FaceMap.RAILING_WALLS)
def create_fill_walls(bm, face, prop):
    # create walls
    wall_size = clamp(prop.wall_fill.width, 0.001, prop.corner_post_width)

    ret = bmesh.ops.duplicate(bm, geom=[face])
    dup_face = filter_geom(ret["geom"], BMFace)[0]
    bmesh.ops.translate(bm, verts=dup_face.verts, vec=-face.normal * wall_size / 2)
    ret = bmesh.ops.extrude_edge_only(bm, edges=dup_face.edges)
    verts = filter_geom(ret["geom"], BMVert)
    bmesh.ops.translate(bm, verts=verts, vec=face.normal * wall_size)
    f = bmesh.ops.contextual_create(bm, geom=verts).get("faces")

    # delete reference faces and hidden faces
    bmesh.ops.delete(bm, geom=[face] + filter_geom(ret["geom"], BMFace), context="FACES")
    return [f[-1], dup_face]


def edge_to_cylinder(bm, edge, radius, up, n=4, fill=False):
    edge_vec = edge_vector(edge)
    theta = (n - 2) * math.pi / n
    length = 2 * radius * math.tan(theta / 2)

    dir = up.copy()
    dir.rotate(Quaternion(edge_vec, -math.pi + theta / 2).to_euler())
    bmesh.ops.translate(bm, verts=edge.verts, vec=dir * radius / math.sin(theta / 2))
    all_verts = [v for v in edge.verts]
    dir.rotate(Quaternion(edge_vec, math.pi - theta / 2).to_euler())
    for i in range(0, n):
        ret = bmesh.ops.extrude_edge_only(bm, edges=[edge])
        edge = filter_geom(ret["geom"], BMEdge)[0]
        bmesh.ops.translate(bm, verts=edge.verts, vec=dir * length)
        dir.rotate(Quaternion(edge_vec, math.radians(360 / n)).to_euler())
        all_verts += edge.verts

    bmesh.ops.remove_doubles(bm, verts=all_verts, dist=0.001)

    if fill:  # fill holes
        valid_verts = [v for v in all_verts if v.is_valid]
        sorted_edges = sort_edges({e for v in valid_verts for e in v.link_edges}, edge_vec)
        top_edges = sorted_edges[-n:]
        bottom_edges = sorted_edges[:n]
        bmesh.ops.holes_fill(bm, edges=top_edges)
        bmesh.ops.holes_fill(bm, edges=bottom_edges)

    return validate(all_verts)


def translate_bounds(bm, verts, dir, trans):
    """ Translate the end verts inwards
    """
    if dir.z: # if rail is sloping, make vector horizontal
        left = dir.cross(VEC_DOWN)
        dir.rotate(Quaternion(left, math.atan(dir.z / dir.xy.length)).to_euler())

    vec = dir.xy*trans
    mid = len(verts) // 2
    vts = sort_verts(verts, dir)
    bmesh.ops.translate(bm, verts=vts[:mid], vec=(vec.x, vec.y, 0.0))
    bmesh.ops.translate(bm, verts=vts[-mid:], vec=(-vec.x, -vec.y, 0.0))


def rotate_faces(bm, cylinder, dir, left, prop):
    """ Rotate the upper and lower faces (align posts to slanted railing)
    """
    mid = len(cylinder) // 2
    vts = sort_verts(cylinder, dir)
    angle = math.atan(left.z / left.xy.length)
    bmesh.ops.rotate(
            bm, verts=vts[-mid:], cent=calc_verts_median(vts[-mid:]),
            matrix=Matrix.Rotation(angle, 4, dir.cross(-left))
        )

    if prop.bottom_rail:
        bmesh.ops.rotate(
                bm, verts=vts[:mid], cent=calc_verts_median(vts[:mid]),
                matrix=Matrix.Rotation(angle, 4, dir.cross(-left))
            )


def rotate_sloped_rail_bounds(bm, cylinder_verts, dir):
    """ Rotate the end faces of sloping cylinder rail to be vertically aligned
    """
    mid = len(cylinder_verts) // 2
    vts = sort_verts(cylinder_verts, dir)
    angle = math.atan(dir.z / dir.xy.length)
    for bunch in [vts[:mid], vts[-mid:]]:
        bmesh.ops.rotate(
            bm, verts=bunch, cent=calc_verts_median(bunch),
            matrix=Matrix.Rotation(angle, 4, dir.cross(VEC_DOWN))
        )

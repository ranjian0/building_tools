import math
import bmesh
from bmesh.types import BMFace, BMEdge, BMVert
from mathutils import Vector, Matrix, Quaternion
from ...utils import (
    clamp,
    FaceMap,
    sort_edges,
    edge_vector,
    filter_geom,
    map_new_faces,
    subdivide_edges,
    calc_edge_median,
    filter_vertical_edges,
    add_facemap_for_groups,
)


def create_railing(bm, faces, prop, normal):
    vertical_edges = list({e for f in faces for e in filter_vertical_edges(f.edges, f.normal)})
    add_facemap_for_groups(FaceMap.RAILING_POSTS)
    make_corner_posts(bm, vertical_edges, prop, faces[0].normal)
    for f in faces:
        make_fill(bm, f, prop)
    bmesh.ops.delete(bm, geom=faces, context="FACES")  # delete reference faces


@map_new_faces(FaceMap.RAILING_POSTS)
def make_corner_posts(bm, edges, prop, up):
    for edge in edges:
        ret = bmesh.ops.duplicate(bm, geom=[edge])
        dup_edge = filter_geom(ret["geom"], BMEdge)[0]
        edge_to_cylinder(bm, dup_edge, prop.corner_post_width/2, up, fill=True)


def make_fill(bm, face, prop):
    # duplicate original face and resize
    ret = bmesh.ops.duplicate(bm, geom=[face])
    dup_face = filter_geom(ret["geom"], BMFace)[0]
    vertical = filter_vertical_edges(dup_face.edges, dup_face.normal)
    non_vertical = [e for e in dup_face.edges if e not in vertical]
    top_edge = sort_edges(non_vertical, Vector((0., 0., -1.)))[0]
    bmesh.ops.translate(bm, verts=top_edge.verts, vec=Vector((0., 0., -1.))*prop.corner_post_width/2)

    # create railing top
    add_facemap_for_groups(FaceMap.RAILING_RAILS)
    create_railing_top(bm, top_edge, prop)

    # create fill
    if prop.fill == "POSTS":
        create_fill_posts(bm, dup_face, prop)
    elif prop.fill == "RAILS":
        create_fill_rails(bm, dup_face, prop)
    elif prop.fill == "WALL":
        add_facemap_for_groups(FaceMap.RAILING_WALLS)
        create_fill_walls(bm, dup_face, prop)


@map_new_faces(FaceMap.RAILING_RAILS)
def create_railing_top(bm, top_edge, prop):
    ret = bmesh.ops.duplicate(bm, geom=[top_edge])
    top_dup_edge = filter_geom(ret["geom"], BMEdge)[0]
    horizon = edge_vector(top_dup_edge).cross(Vector((0., 0., 1.)))
    up = edge_vector(top_dup_edge)
    up.rotate(Quaternion(horizon, math.pi/2).to_euler())

    if not edge_vector(top_dup_edge).z:
        scale_railing_edge(bm, top_dup_edge, prop.corner_post_width)

    edge_to_cylinder(bm, top_dup_edge, prop.corner_post_width/2, up)
    bmesh.ops.translate(bm, verts=top_edge.verts, vec=Vector((0., 0., -1.))*prop.corner_post_width/2)


@map_new_faces(FaceMap.RAILING_POSTS)
def create_fill_posts(bm, face, prop):
    vertical_edges = filter_vertical_edges(face.edges, face.normal)
    sorted_edges = sort_edges([e for e in face.edges if e not in vertical_edges], Vector((0., 0., -1.)))

    # create posts
    post_size = min(prop.post_fill.size, prop.corner_post_width)

    top_edge = sorted_edges[0]
    bottom_edge = sorted_edges[-1]
    top_edge_vector = top_edge.verts[0].co - top_edge.verts[1].co
    top_edge_vector.z = 0
    n_posts = round(top_edge_vector.length*prop.post_fill.density/post_size)
    dir = edge_vector(top_edge)
    if n_posts != 0:
        inner_edges = subdivide_edges(bm, [top_edge, bottom_edge], dir, widths=[1.]*(n_posts+1))
        for edge in inner_edges:
            ret = bmesh.ops.duplicate(bm, geom=[edge])
            dup_edge = filter_geom(ret["geom"], BMEdge)[0]
            up = face.normal
            edge_to_cylinder(bm, dup_edge, post_size/2, up)
        # delete reference faces
        dup_faces = list({f for e in inner_edges for f in e.link_faces})
        bmesh.ops.delete(bm, geom=dup_faces, context="FACES")
    else:
        # delete reference faces
        bmesh.ops.delete(bm, geom=[face], context="FACES")


@map_new_faces(FaceMap.RAILING_RAILS)
def create_fill_rails(bm, face, prop):
    # create rails
    rail_size = min(prop.rail_fill.size, prop.corner_post_width)

    vertical_edges = filter_vertical_edges(face.edges, face.normal)
    n_rails = math.floor(vertical_edges[0].calc_length()*prop.rail_fill.density/rail_size)
    if n_rails != 0:
        inner_edges = subdivide_edges(bm, vertical_edges, Vector((0., 0., 1.)), widths=[1.]*(n_rails+1))
        for edge in inner_edges:
            ret = bmesh.ops.duplicate(bm, geom=[edge])
            dup_edge = filter_geom(ret["geom"], BMEdge)[0]
            up = face.normal
            if not edge_vector(dup_edge).z:
                scale_railing_edge(bm, dup_edge, prop.corner_post_width)
            edge_to_cylinder(bm, dup_edge, rail_size/2, up)
        # delete reference faces
        dup_faces = list({f for e in inner_edges for f in e.link_faces})
        bmesh.ops.delete(bm, geom=dup_faces, context="FACES")
    else:
        # delete reference faces
        bmesh.ops.delete(bm, geom=[face], context="FACES")


@map_new_faces(FaceMap.RAILING_WALLS)
def create_fill_walls(bm, face, prop):
    # create walls
    wall_size = clamp(prop.wall_fill.width, 0.001, prop.corner_post_width)

    ret = bmesh.ops.duplicate(bm, geom=[face])
    dup_face = filter_geom(ret["geom"], BMFace)[0]
    bmesh.ops.translate(bm, verts=dup_face.verts, vec=-face.normal*wall_size/2)
    ret = bmesh.ops.extrude_edge_only(bm, edges=dup_face.edges)
    verts = filter_geom(ret["geom"], BMVert)
    bmesh.ops.translate(bm, verts=verts, vec=face.normal*wall_size)
    bmesh.ops.contextual_create(bm, geom=verts)

    # delete reference faces and hidden faces
    bmesh.ops.delete(bm, geom=[face] + filter_geom(ret['geom'], BMFace), context="FACES")


def edge_to_cylinder(bm, edge, radius, up, n=4, fill=False):
    edge_vec = edge_vector(edge)
    theta = (n-2)*math.pi/n
    length = 2 * radius * math.tan(theta/2)

    dir = up.copy()
    dir.rotate(Quaternion(edge_vec, -math.pi+theta/2).to_euler())
    bmesh.ops.translate(bm, verts=edge.verts, vec=dir*radius/math.sin(theta/2))
    all_verts = [v for v in edge.verts]
    dir.rotate(Quaternion(edge_vec, math.pi-theta/2).to_euler())
    for i in range(0, n):
        ret = bmesh.ops.extrude_edge_only(bm, edges=[edge])
        edge = filter_geom(ret["geom"], BMEdge)[0]
        bmesh.ops.translate(bm, verts=edge.verts, vec=dir*length)
        dir.rotate(Quaternion(edge_vec, math.radians(360/n)).to_euler())
        all_verts += edge.verts

    bmesh.ops.remove_doubles(bm, verts=all_verts, dist=0.001)

    if fill:  # fill holes
        valid_verts = [v for v in all_verts if v.is_valid]
        sorted_edges = sort_edges({e for v in valid_verts for e in v.link_edges}, edge_vec)
        top_edges = sorted_edges[-n:]
        bottom_edges = sorted_edges[:n]
        bmesh.ops.holes_fill(bm, edges=top_edges)
        bmesh.ops.holes_fill(bm, edges=bottom_edges)


def scale_railing_edge(bm, edge, amount):
    edge_len = edge.calc_length()
    edge_scale = (edge_len - amount) / edge_len
    bmesh.ops.scale(bm,
                    verts=edge.verts,
                    vec=Vector((1., 1., 1.))*edge_scale,
                    space=Matrix.Translation(-calc_edge_median(edge)))

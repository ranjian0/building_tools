import bmesh
import operator
import math

from mathutils import Vector, Quaternion, Euler
from bmesh.types import BMVert, BMFace, BMEdge

from ...utils import (
    FaceMap,
    is_ngon,
    filter_geom,
    popup_message,
    add_faces_to_map,
    create_face,
    local_xyz,
    subdivide_face_vertically,
    sort_faces,
    sort_verts,
)

from ..railing.railing import create_railing

def create_stairs(bm, faces, prop):
    """Extrude steps from selected faces
    """

    for f in faces:
        f.select = False
        if is_ngon(f):
            popup_message("Stair creation not supported for n-gons!", "Ngon Error")
            return False

        f = create_stairs_split(bm, f, prop)
        add_faces_to_map(bm, [f], FaceMap.STAIRS)

        normal = f.normal
        top_faces = create_steps(bm, f, prop)

        if prop.has_railing:
            add_railing_to_stairs(bm, top_faces, normal, prop)

        return True


def create_steps(bm, face, prop):
    """ Create stair steps with landing"""
    
    top_faces = []

    # create landing
    if prop.landing:
        face = extrude_step(bm, face, prop.landing_width)
        top_faces.append(list({f for e in face.edges for f in e.link_faces if f.normal.z > 0}).pop())

    # create steps
    for i in range(prop.step_count):
        ret_face = subdivide_next_step(bm, face, prop.step_count-i, prop.step_height)
        face = extrude_step(bm, ret_face, prop.step_width)

        # -- keep reference to top faces for railing
        faces = {f for e in face.edges for f in e.link_faces if f.normal.z > 0}
        top_faces.append(list(faces).pop())

    return top_faces


def extrude_step(bm, face, step_width):
    """ Extrude a stair step
    """
    n = face.normal
    ret_face = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces").pop()
    bmesh.ops.translate(bm, vec=n * step_width, verts=ret_face.verts)
    return ret_face


def subdivide_next_step(bm, ret_face, remaining, step_height):
    """ cut the next face step height
    """
    return subdivide_face_vertically(bm, ret_face, widths=[remaining*step_height, step_height])[0]


def create_stairs_split(bm, face, prop):
    """Use properties to create face
    """
    xyz = local_xyz(face)
    size = Vector((prop.size_offset.size.x, (prop.step_count+1)*prop.step_height))
    f = create_face(bm, size, prop.size_offset.offset, xyz)
    bmesh.ops.translate(
        bm, verts=f.verts, vec=face.calc_center_bounds() - face.normal*prop.depth
    )
    return f


def add_railing_to_stairs(bm, top_faces, normal, prop):
    steps = sort_faces(top_faces, normal)
    first_step = steps[0]
    last_step = steps[-1]

    # create railing initial edges
    if prop.landing:
        v1, v2 = railing_verts(bm, sort_verts(first_step.verts, normal)[:2], normal, prop.rail.offset, prop.step_width/2)
        v3, v4 = railing_verts(bm, sort_verts(first_step.verts, normal)[-2:], normal, prop.rail.offset, -prop.step_width/2)
        v5, v6 = railing_verts(bm, sort_verts(last_step.verts, normal)[:2], normal, prop.rail.offset, prop.step_width/2)
        e1 = bmesh.ops.contextual_create(bm, geom=(v1, v3))["edges"][0]
        e2 = bmesh.ops.contextual_create(bm, geom=[v3, v5])["edges"][0]
        e3 = bmesh.ops.contextual_create(bm, geom=[v2, v4])["edges"][0]
        e4 = bmesh.ops.contextual_create(bm, geom=[v4, v6])["edges"][0]
        railing_edges = [e1, e2, e3, e4]
    else:
        v1, v2 = railing_verts(bm, sort_verts(first_step.verts, normal)[:2], normal, prop.rail.offset, prop.step_width/2)
        v3, v4 = railing_verts(bm, sort_verts(last_step.verts, normal)[:2], normal, prop.rail.offset, prop.step_width/2)
        e1 = bmesh.ops.contextual_create(bm, geom=(v1, v3))["edges"][0]
        e2 = bmesh.ops.contextual_create(bm, geom=[v2, v4])["edges"][0]
        railing_edges = [e1, e2]

    # extrude edges
    ret = bmesh.ops.extrude_edge_only(bm, edges=railing_edges)
    top_edges = filter_geom(ret["geom"], BMEdge)
    top_verts = list({v for e in top_edges for v in e.verts})
    bmesh.ops.translate(bm, verts=top_verts, vec=Vector((0., 0., 1.))*prop.rail.corner_post_height)
    railing_faces = filter_geom(ret["geom"], BMFace)

    create_railing(bm, railing_faces, prop.rail, normal)


def railing_verts(bm, verts, normal, offset, depth):
    tangent = normal.copy()
    tangent.rotate(Quaternion(Vector((0., 0., 1.)), math.pi/2).to_euler())
    co1 = verts[0].co + depth * normal
    co2 = verts[1].co + depth * normal
    v1 = bmesh.ops.create_vert(bm, co=co1)["vert"][0]
    v2 = bmesh.ops.create_vert(bm, co=co2)["vert"][0]
    bmesh.ops.translate(bm, verts=[v1], vec=tangent*offset)
    bmesh.ops.translate(bm, verts=[v2], vec=-tangent*offset)
    return v1, v2

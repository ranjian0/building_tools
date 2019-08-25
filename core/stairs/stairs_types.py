import bmesh
import operator
import functools
from mathutils import Vector
from bmesh.types import BMVert
from collections import defaultdict

from ..rails import create_railing_from_edges, create_railing_from_step_edges
from ...utils import (
    FaceMap,
    filter_geom,
    add_faces_to_map,
    inset_face_with_scale_offset,
    subdivide_face_edges_horizontal,
)


def create_stairs(bm, faces, prop):
    """Extrude steps from selected faces
    """

    for f in faces:
        f.select = False
        f = create_stair_split(bm, f, prop.size_offset)

        add_faces_to_map(bm, [f], FaceMap.STAIRS)

        # -- options for railing
        top_faces = []
        init_normal = f.normal.copy()

        f = create_landing(bm, f, top_faces, prop)
        create_steps(bm, f, top_faces, prop)

    if prop.railing:
        create_stairs_railing(bm, init_normal, top_faces, prop)


def create_landing(bm, f, top_faces, prop):
    """ Create stair landing """
    if prop.landing:
        ret_face = extrude_step(bm, f, prop.landing_width)

        # -- keep reference to top faces for railing
        faces = {f for e in ret_face.edges for f in e.link_faces if f.normal.z > 0}
        top_faces.append(list(faces).pop())

        return get_stair_face_from_direction(bm, ret_face, prop)
    return f


def create_steps(bm, f, top_faces, prop):
    """ Create stair steps """
    ext_face = f
    get_z = operator.attrgetter("co.z")
    fheight = max(f.verts, key=get_z).co.z - min(f.verts, key=get_z).co.z

    step_size = fheight / (prop.step_count + 1)
    start_loc = max(f.verts, key=get_z).co.z
    for i in range(prop.step_count):
        offset = start_loc - (step_size * (i+1))
        ret_face = subdivide_next_step(bm, ext_face, offset)

        ext_face = extrude_step(bm, ret_face, prop.step_width)

        # -- keep reference to top faces for railing
        faces = {f for e in ext_face.edges for f in e.link_faces if f.normal.z > 0}
        top_faces.append(list(faces).pop())


def extrude_step(bm, face, step_width):
    """ Extrude a stair step
    """
    n = face.normal
    ret_face = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces").pop()
    bmesh.ops.translate(bm, vec=n * step_width, verts=ret_face.verts)
    return ret_face


def get_stair_face_from_direction(bm, ret_face, prop):
    """ adjust ret_face based on stair direction
    """
    faces = list({f for e in ret_face.edges for f in e.link_faces})
    left_normal, right_normal = (
        ret_face.normal.cross(Vector((0, 0, 1))),
        ret_face.normal.cross(Vector((0, 0, -1))),
    )

    def flt(f, normal):
        return f.normal.to_tuple(4) == normal.to_tuple(4)

    left = next(filter(lambda f: flt(f, left_normal), faces))
    right = next(filter(lambda f: flt(f, right_normal), faces))

    return {"LEFT": left, "RIGHT": right}.get(prop.stair_direction, ret_face)


def subdivide_next_step(bm, ret_face, offset):
    """ cut the next face step height
    """
    res = subdivide_face_edges_horizontal(bm, ret_face, cuts=1)
    verts = filter_geom(res["geom_inner"], BMVert)
    for v in verts:
        v.co.z = offset
    return min(verts.pop().link_faces, key=lambda f: f.calc_center_median().z)


def create_stair_split(bm, face, prop):
    """Use properties from SplitOffset to subdivide face into regular quads
    """
    size, off = prop.size, prop.offset
    return inset_face_with_scale_offset(bm, face, size.y, size.x, off.x, off.y, off.z)


def create_stairs_railing(bm, normal, faces, prop):
    """Create railing for stairs
    """
    # -- create railing for landing
    if prop.landing:
        landing_face = faces.pop(0)
        EDGES = functools.partial(edges_from_direction, landing_face, normal)
        if prop.stair_direction == "FRONT":
            create_railing_from_edges(bm, EDGES(["LEFT", "RIGHT"]), prop.rail)
        elif prop.stair_direction == "LEFT":
            create_railing_from_edges(bm, EDGES(["FRONT", "RIGHT"]), prop.rail)
        elif prop.stair_direction == "RIGHT":
            create_railing_from_edges(bm, EDGES(["LEFT", "FRONT"]), prop.rail)

    # --create railing for steps
    create_step_railing(bm, normal, faces, prop)


def create_step_railing(bm, normal, faces, prop):
    """Create railing for stair steps
    """

    # -- update normal based on stair direction
    if prop.stair_direction == "LEFT":
        normal = normal.cross(Vector((0, 0, 1)))
    elif prop.stair_direction == "RIGHT":
        normal = normal.cross(Vector((0, 0, -1)))

    # -- get all left and right edges
    left_edges, right_edges = [], []
    for face in faces:
        EDGES = functools.partial(edges_from_direction, face, normal)
        left_edges.extend(EDGES(["LEFT"]))
        right_edges.extend(EDGES(["RIGHT"]))

    # -- filter edges based on direction
    valid_edges = {
        "LEFT": right_edges,
        "RIGHT": left_edges,
        "FRONT": left_edges + right_edges,
    }.get(prop.stair_direction)
    create_railing_from_step_edges(bm, valid_edges, normal, prop)


def edges_from_direction(face, normal, direction):
    edges = defaultdict(list)
    edges.fromkeys(["FRONT", "LEFT", "RIGHT"])

    valid_loops = [l for l in face.loops]
    for e in face.edges:
        for loop in e.link_loops:
            if loop in valid_loops:
                tan = e.calc_tangent(loop)
                if tan == -normal:
                    edges["FRONT"].append(e)

                if round(normal.cross(tan).z) < 0:
                    edges["RIGHT"].append(e)

                if round(normal.cross(tan).z) > 0:
                    edges["LEFT"].append(e)

    return sum([edges[d] for d in list(direction)], [])

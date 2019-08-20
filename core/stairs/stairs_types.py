import bmesh
import operator
from mathutils import Vector
from bmesh.types import BMVert

from ..rails import create_railing_from_edges, create_railing_from_step_edges
from ...utils import (
    filter_geom,
    inset_face_with_scale_offset,
    subdivide_face_edges_horizontal,
)


def create_stairs(bm, faces, prop):
    """Extrude steps from selected faces
    """

    for f in faces:
        f.select = False
        f = create_stair_split(bm, f, prop.size_offset)

        get_z = operator.attrgetter("co.z")
        fheight = max(f.verts, key=get_z).co.z - min(f.verts, key=get_z).co.z

        # -- options for railing
        top_faces = []
        init_normal = f.normal.copy()

        ext_face = f
        step_count = prop.step_count + (1 if prop.landing else 0)
        for i in range(step_count):
            ret_face = extrude_step(bm, i, ext_face, prop)

            # -- keep reference to top faces for railing
            faces = {f for e in ret_face.edges for f in e.link_faces if f.normal.z > 0}
            top_faces.append(list(faces).pop())

            if prop.landing and i == 0:
                ret_face = get_stair_face_from_direction(bm, ret_face, prop)

            if i < (step_count - 1):
                ext_face = subdivide_next_step(bm, ret_face, fheight, step_count, i)

    if prop.railing:
        create_stairs_railing(bm, init_normal, top_faces, prop)


def extrude_step(bm, step_idx, face, prop):
    """ Extrude a stair step
    """
    n = face.normal
    ext_width = (
        prop.landing_width if (prop.landing and step_idx == 0) else prop.step_width
    )
    ret_face = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces").pop()
    bmesh.ops.translate(bm, vec=n * ext_width, verts=ret_face.verts)
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

    if prop.stair_direction == "LEFT":
        return left
    elif prop.stair_direction == "RIGHT":
        return right
    return ret_face


def subdivide_next_step(bm, ret_face, fheight, step_count, step_idx):
    """ cut the next face step height
    """
    res = subdivide_face_edges_horizontal(bm, ret_face, 1)
    bmesh.ops.translate(
        bm,
        verts=filter_geom(res["geom_inner"], BMVert),
        vec=(0, 0, (fheight / 2) - (fheight / (step_count - step_idx))),
    )

    return min(
        filter_geom(res["geom_inner"], BMVert).pop().link_faces,
        key=lambda f: f.calc_center_median().z,
    )


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
        landing_face, *step_faces = faces

        if prop.stair_direction == "FRONT":
            create_railing_front(bm, landing_face, normal, prop.rail)
        elif prop.stair_direction == "LEFT":
            create_railing_left(bm, landing_face, normal, prop.rail)
        elif prop.stair_direction == "RIGHT":
            create_railing_right(bm, landing_face, normal, prop.rail)

    else:
        step_faces = faces

    # --create railing for steps
    create_step_railing(bm, normal, step_faces, prop)


def create_railing_front(bm, face, normal, prop):
    """Create rails for landing when stair direction is front
    """

    # -- determine left and right edges
    valid_edges = []
    valid_loops = [l for l in face.loops]
    for e in face.edges:
        for loop in e.link_loops:
            if loop in valid_loops:
                tan = e.calc_tangent(loop)
                if round(normal.cross(tan).z):
                    valid_edges.append(e)

    create_railing_from_edges(bm, valid_edges, prop)


def create_railing_left(bm, face, normal, prop):
    """Create rails for landing when stair direction is left
    """

    # -- determine front and left edges
    valid_edges = []
    valid_loops = [l for l in face.loops]
    for e in face.edges:
        for loop in e.link_loops:
            if loop in valid_loops:
                tan = e.calc_tangent(loop)
                if tan == -normal:
                    valid_edges.append(e)

                if round(normal.cross(tan).z) < 0:
                    valid_edges.append(e)

    create_railing_from_edges(bm, valid_edges, prop)


def create_railing_right(bm, face, normal, prop):
    """Create rails for landing when stair direction is right
    """

    # -- determine front and right edges
    valid_edges = []
    valid_loops = [l for l in face.loops]
    for e in face.edges:
        for loop in e.link_loops:
            if loop in valid_loops:
                tan = e.calc_tangent(loop)
                if tan == -normal:
                    valid_edges.append(e)

                if round(normal.cross(tan).z) > 0:
                    valid_edges.append(e)

    create_railing_from_edges(bm, valid_edges, prop)


def create_step_railing(bm, normal, faces, prop):
    """Create railing for stair steps
    """

    # -- update normal based on stair direction
    if prop.stair_direction == "LEFT":
        normal = normal.cross(Vector((0, 0, 1)))
    elif prop.stair_direction == "RIGHT":
        normal = normal.cross(Vector((0, 0, -1)))

    # -- get all left and right edges
    left_edges = []
    right_edges = []

    for face in faces:
        for edge in face.edges:
            for loop in edge.link_loops:
                if loop in [l for l in face.loops]:
                    tan = edge.calc_tangent(loop)

                    if round(normal.cross(tan).z) < 0:
                        right_edges.append(edge)

                    if round(normal.cross(tan).z) > 0:
                        left_edges.append(edge)

    # -- filter edges based on direction
    valid_edges = []
    if prop.stair_direction == "FRONT":
        valid_edges.extend(left_edges + right_edges)
    elif prop.stair_direction == "LEFT":
        valid_edges.extend(right_edges)
    elif prop.stair_direction == "RIGHT":
        valid_edges.extend(left_edges)

    create_railing_from_step_edges(bm, valid_edges, normal, prop)

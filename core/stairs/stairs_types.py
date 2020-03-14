import bmesh
import operator

from bmesh.types import BMVert


from ...utils import (
    FaceMap,
    filter_geom,
    add_faces_to_map,
    inset_face_with_scale_offset,
    subdivide_face_edges_horizontal,
    local_to_global,
    calc_face_dimensions,
)

from mathutils import Vector


def create_stairs(bm, faces, prop):
    """Extrude steps from selected faces
    """

    for f in faces:
        f.select = False
        f = create_stair_split(bm, f, prop.size_offset)

        add_faces_to_map(bm, [f], FaceMap.STAIRS)

        # -- options for railing
        top_faces = []

        f = create_landing(bm, f, top_faces, prop)
        create_steps(bm, f, top_faces, prop)


def create_landing(bm, f, top_faces, prop):
    """ Create stair landing """
    if prop.landing:
        ret_face = extrude_step(bm, f, prop.landing_width)

        # -- keep reference to top faces for railing
        faces = {f for e in ret_face.edges for f in e.link_faces if f.normal.z > 0}
        top_faces.append(list(faces).pop())

        return ret_face
    return f


def create_steps(bm, f, top_faces, prop):
    """ Create stair steps """
    ext_face = f
    get_z = operator.attrgetter("co.z")
    fheight = max(f.verts, key=get_z).co.z - min(f.verts, key=get_z).co.z

    step_size = fheight / (prop.step_count + 1)
    start_loc = max(f.verts, key=get_z).co.z
    for i in range(prop.step_count):
        idx = i + 1 if prop.landing else i
        offset = start_loc - (step_size * idx)
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
    wall_w, wall_h = calc_face_dimensions(face)
    scale_x = prop.size.x/wall_w
    scale_y = prop.size.y/wall_h
    offset = local_to_global(face, Vector((prop.offset.x, prop.offset.y, 0.0)))
    return inset_face_with_scale_offset(bm, face, scale_y, scale_x, offset.x, offset.y, offset.z)

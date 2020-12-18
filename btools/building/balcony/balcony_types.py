import math
import bmesh
from bmesh.types import BMVert, BMFace, BMEdge
from mathutils import Vector

from ..railing.railing import create_railing
from ...utils import (
    clamp,
    VEC_UP,
    FaceMap,
    validate,
    local_xyz,
    sort_verts,
    sort_edges,
    valid_ngon,
    filter_geom,
    create_face,
    ngon_to_quad,
    get_top_faces,
    calc_edge_median,
    add_faces_to_map,
    get_selection_groups,
    calc_face_dimensions,
)


def create_balcony(bm, faces, prop):
    """Generate balcony geometry
    """
    create_function = [
        create_balcony_ungrouped, create_balcony_grouped
    ][prop.group_selection]
    create_function(bm, faces, prop)


def create_balcony_grouped(bm, faces, prop):
    """ Make a single balcony on each group of adjacent selected faces
    """
    selection_groups = get_selection_groups(bm)
    if all(len(group) == 1 for group in selection_groups):
        # -- user has no adjacent selections, do ungrouped balcony
        create_balcony_ungrouped(bm, sum(selection_groups, []), prop)
        return

    for faces in selection_groups:
        [f.select_set(False) for f in faces]
        group = filter_geom(bmesh.ops.duplicate(bm, geom=faces)['geom'], BMFace)
        transform_grouped_faces(bm, group, prop)
        top_faces = extrude_balcony_grouped(bm, group, prop.depth)

        if prop.has_railing:
            top_face = bmesh.ops.dissolve_faces(bm, faces=top_faces)['region'].pop()
            add_railing_to_balcony_grouped(bm, top_face, prop)


def create_balcony_ungrouped(bm, faces, prop):
    """ Make a balcony on each face selection
    """
    for f in faces:
        f.select = False
        if not valid_ngon(f):
            ngon_to_quad(bm, f)

        normal = f.normal.copy()
        split_faces = create_balcony_split(bm, f, prop)
        for f in split_faces:
            add_faces_to_map(bm, [f], FaceMap.BALCONY)
            front, top = extrude_balcony(bm, f, prop.depth, normal)

            if prop.has_railing:
                prop.rail.show_extra_props = True
                add_railing_to_balcony(bm, top, normal, prop)
            bmesh.ops.delete(bm, geom=[f], context="FACES_ONLY")


def extrude_balcony(bm, face, depth, normal):
    front = filter_geom(bmesh.ops.extrude_face_region(bm, geom=[face])["geom"], BMFace)[0]
    map_balcony_faces(bm, front)
    bmesh.ops.translate(bm, verts=front.verts, vec=normal * depth)

    top = get_top_faces(f for e in front.edges for f in e.link_faces)[0]
    return front, top


def extrude_balcony_grouped(bm, group, depth):
    """ Extrude adjacent selected faces as one
    """

    def splitones(num):
        """ Return a list of numbers that add up to num where the largest value is one
        """
        fract, intr = math.modf(num)
        result = [1 for _ in range(int(intr))]
        if fract > 0.0:
            result.append(fract)
        return result

    result = []
    inset_faces = group[:]
    valid_normals = [f.normal.to_tuple(3) for f in group]
    for num in splitones(depth):
        res = bmesh.ops.inset_region(
            bm, faces=inset_faces, depth=num, use_even_offset=True, use_boundary=True)["faces"]
        bmesh.ops.dissolve_degenerate(
            bm, dist=0.001, edges=list({e for f in inset_faces for e in f.edges}))
        inset_faces = validate(inset_faces)
        inset_faces.extend([f for f in res if f.normal.to_tuple(3) in valid_normals])
        result.extend(res)
    return [f for f in validate(result) if f.normal.z > 0]


def add_railing_to_balcony(bm, top, balcony_normal, prop):
    """Add railing to the balcony
    """
    ret = bmesh.ops.duplicate(bm, geom=[top])
    dup_top = filter_geom(ret["geom"], BMFace)[0]

    max_offset = min([*calc_face_dimensions(dup_top)]) / 2
    prop.rail.offset = clamp(prop.rail.offset, 0.0, max_offset - 0.001)
    ret = bmesh.ops.inset_individual(
        bm, faces=[dup_top], thickness=prop.rail.offset, use_even_offset=True
    )
    bmesh.ops.delete(bm, geom=ret["faces"], context="FACES")

    edges = sort_edges(dup_top.edges, balcony_normal)[1:]
    railing_geom = bmesh.ops.extrude_edge_only(bm, edges=edges)["geom"]
    bmesh.ops.translate(
        bm, verts=filter_geom(railing_geom, BMVert), vec=(0., 0., prop.rail.corner_post_height)
    )

    bmesh.ops.delete(bm, geom=[dup_top], context="FACES")

    railing_faces = filter_geom(railing_geom, BMFace)
    create_railing(bm, railing_faces, prop.rail, balcony_normal)


def add_railing_to_balcony_grouped(bm, top, prop):
    """ Create railing for grouped selection balcony
    """
    old_boundary_edges = [e for e in top.edges if len(e.link_faces) > 1]

    ret = bmesh.ops.duplicate(bm, geom=[top])
    boundary_edges = [ret['edge_map'][obe] for obe in old_boundary_edges]
    dup_top = filter_geom(ret["geom"], BMFace)[0]

    max_offset = min([*calc_face_dimensions(dup_top)]) / 2
    prop.rail.offset = clamp(prop.rail.offset, 0.0, max_offset - 0.001)
    ret = bmesh.ops.inset_individual(
        bm, faces=[dup_top], thickness=prop.rail.offset, use_even_offset=True
    )
    bmesh.ops.delete(bm, geom=ret["faces"], context="FACES")
    dup_edges = filter_geom(bmesh.ops.duplicate(bm, geom=boundary_edges)['geom'], BMEdge)

    railing_geom = bmesh.ops.extrude_edge_only(bm, edges=dup_edges)["geom"]
    bmesh.ops.translate(
        bm, verts=filter_geom(railing_geom, BMVert), vec=(0., 0., prop.rail.corner_post_height)
    )
    bmesh.ops.delete(bm, geom=[dup_top], context="FACES")
    railing_faces = filter_geom(railing_geom, BMFace)
    create_railing(bm, railing_faces, prop.rail, Vector())


def map_balcony_faces(bm, face):
    """ Add balcony faces to their facemap """
    new_faces = {f for e in face.edges for f in e.link_faces}
    add_faces_to_map(bm, new_faces, FaceMap.BALCONY)


def create_balcony_split(bm, face, prop):
    """Use properties to create face
    """
    xyz = local_xyz(face)
    face_w, face_h = calc_face_dimensions(face)
    # TODO(ranjian0) Take into consideration the offset of a balcony when clamping width
    width = min(face_w, prop.width)
    height = max(0, prop.height)
    count = min(prop.count, int(face_w / prop.width))

    result = []
    array_dist = face_w / count
    start = face.calc_center_median() + (xyz[0] * (face_w / 2))
    for i in range(count):
        f = create_face(
            bm, Vector((width, height)), prop.size_offset.offset + Vector((0, -(face_h - height) / 2)), xyz
        )
        off = ((i * array_dist) * -xyz[0]) + ((array_dist/2) * -xyz[0])
        bmesh.ops.translate(
            bm, verts=f.verts, vec=start + off - face.normal*prop.depth_offset
        )
        result.append(f)

    prop.count = count
    return result


def transform_grouped_faces(bm, faces, prop):
    """ Make the height the faces target height starting from the bottom
    """
    face_height = max(map(lambda f: calc_face_dimensions(f)[1], faces))
    target_height = clamp(prop.height, 0.01, face_height)
    prop.height = target_height

    trans_offset = target_height - face_height
    verts = list({v for f in faces for v in f.verts})
    top_verts = sort_verts(verts, VEC_UP)[len(verts) // 2:]
    bmesh.ops.translate(bm, verts=top_verts, vec=VEC_UP * trans_offset)
    bmesh.ops.translate(bm, verts=verts, vec=VEC_UP * prop.height)


def top_face_edges(faces):
    """ Return all the upper edges in faces
    """
    top_edges = list({e for f in faces for e in f.edges})
    return sorted(top_edges, key=lambda e : calc_edge_median(e).z, reverse=True)[:len(faces)]

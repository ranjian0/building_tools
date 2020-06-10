import bmesh
from enum import Enum, auto
from mathutils import Vector, Matrix
from bmesh.types import BMEdge, BMVert
from ...utils import (
    FaceMap,
    validate,
    filter_geom,
    map_new_faces,
    add_faces_to_map,
    calc_edge_median,
    calc_face_dimensions,
    filter_vertical_edges,
    filter_horizontal_edges,
)


class FillUser(Enum):
    DOOR = auto()
    WINDOW = auto()


@map_new_faces(FaceMap.FRAME, skip=FaceMap.DOOR_PANELS)
def fill_panel(bm, face, prop):
    """Create panels on face
    """
    if prop.panel_count_x + prop.panel_count_y == 0:
        return

    width, height = calc_face_dimensions(face)
    if not round(width) or not round(height):
        return

    # XXX Ensure panel border is less than parent face size
    min_dimension = min(calc_face_dimensions(face))
    prop.panel_border_size = min(
        prop.panel_border_size, min_dimension / 2)

    bmesh.ops.inset_individual(bm, faces=[face], thickness=prop.panel_border_size)
    quads = subdivide_face_into_quads(bm, face, prop.panel_count_x, prop.panel_count_y)

    # XXX Ensure panel margin is less that size of each quad)
    min_dimension = min(sum([calc_face_dimensions(q) for q in quads], ()))
    prop.panel_margin = min(prop.panel_margin, min_dimension / 2)

    bmesh.ops.inset_individual(
        bm, faces=quads, thickness=prop.panel_margin, use_even_offset=True
    )
    bmesh.ops.translate(
        bm,
        verts=list({v for f in quads for v in f.verts}),
        vec=face.normal * prop.panel_depth,
    )
    add_faces_to_map(bm, quads, FaceMap.DOOR_PANELS)


def fill_glass_panes(bm, face, prop, user=FillUser.DOOR):
    """Create glass panes on face
    """
    if prop.pane_count_x + prop.pane_count_y == 0:
        return

    width, height = calc_face_dimensions(face)
    if not round(width) or not round(height):
        return

    userframe = FaceMap.DOOR_PANES if user == FillUser.DOOR else FaceMap.WINDOW_PANES
    bmesh.ops.inset_individual(bm, faces=[face], thickness=0.0001) # to isolate the working quad and not leave adjacent face as n-gon
    quads = subdivide_face_into_quads(bm, face, prop.pane_count_x, prop.pane_count_y)

    # XXX Ensure pane margin is less that size of each quad)
    min_dimension = min(sum([calc_face_dimensions(q) for q in quads], ()))
    prop.pane_margin = min(prop.pane_margin, min_dimension / 2)

    inset = map_new_faces(userframe)(bmesh.ops.inset_individual)
    inset(
        bm, faces=quads, thickness=prop.pane_margin,
        depth=-prop.pane_depth, use_even_offset=True
    )

    usergroup = FaceMap.DOOR if user == FillUser.DOOR else FaceMap.WINDOW
    add_faces_to_map(bm, quads, usergroup)


@map_new_faces(FaceMap.WINDOW_BARS)
def fill_bar(bm, face, prop):
    """Create horizontal and vertical bars along a face
    """
    if prop.bar_count_x + prop.bar_count_y == 0:
        return

    face_center = face.calc_center_median()
    width, height = calc_face_dimensions(face)

    # XXX bar width should not exceed window size
    min_dimension = min(
        [width / max(prop.bar_count_x, 1), height / max(prop.bar_count_y, 1)]
    )
    prop.bar_width = min(prop.bar_width, min_dimension)

    # -- horizontal
    offset = height / (prop.bar_count_x + 1)
    for i in range(prop.bar_count_x):
        scale = (1, 1, prop.bar_width / height)
        position = Vector((face.normal * prop.bar_depth)) + Vector(
            (0, 0, -height / 2 + (i + 1) * offset)
        )
        depth = -face.normal * prop.bar_depth
        create_bar_from_face(bm, face, face_center, position, scale, depth)

    # -- vertical
    eps = 0.015
    offset = width / (prop.bar_count_y + 1)
    for i in range(prop.bar_count_y):
        scale = (prop.bar_width / width, prop.bar_width / width, 1)
        perp = face.normal.cross(Vector((0, 0, 1)))
        position = Vector((face.normal * ((prop.bar_depth) - eps))) + perp * (
            -width / 2 + ((i + 1) * offset)
        )
        depth = -face.normal * ((prop.bar_depth) - eps)
        create_bar_from_face(bm, face, face_center, position, scale, depth, True)


def fill_louver(bm, face, prop, user=FillUser.DOOR):
    """Create louvers from face
    """
    normal = face.normal.copy()
    if prop.louver_margin:
        # XXX Louver margin should not exceed smallest face dimension
        prop.louver_margin = min(prop.louver_margin, min(calc_face_dimensions(face)) / 2)
        inset = map_new_faces(FaceMap.FRAME)(bmesh.ops.inset_individual)
        inset(bm, faces=[face], thickness=prop.louver_margin)

    segments = double_and_make_even(prop.louver_count)
    faces = subdivide_face_into_vertical_segments(bm, face, segments)
    faces.sort(key=lambda f: f.calc_center_median().z)
    louver_faces = faces[1::2]

    # -- scale to border
    for face in louver_faces:
        bmesh.ops.scale(
            bm,
            vec=(1, 1, 1 + prop.louver_border),
            verts=face.verts,
            space=Matrix.Translation(-face.calc_center_median()),
        )

    usergroup = [FaceMap.WINDOW_LOUVERS, FaceMap.DOOR_LOUVERS][user == FillUser.DOOR]
    extrude = map_new_faces(usergroup)(extrude_faces_add_slope)
    extrude(bm, louver_faces, normal, prop.louver_depth)
    add_faces_to_map(bm, validate(faces[::2]), usergroup)


def subdivide_face_into_quads(bm, face, cuts_x, cuts_y):
    """subdivide a face(quad) into more quads
    """
    v_edges = filter_vertical_edges(face.edges, face.normal)
    h_edges = filter_horizontal_edges(face.edges, face.normal)

    edges = []
    if cuts_x > 0:
        res = bmesh.ops.subdivide_edges(bm, edges=v_edges, cuts=cuts_x)
        edges.extend(filter_geom(res["geom_inner"], BMEdge))

    if cuts_y > 0:
        res = bmesh.ops.subdivide_edges(bm, edges=h_edges + edges, cuts=cuts_y)
        edges.extend(filter_geom(res["geom_inner"], BMEdge))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
    return list({f for ed in validate(edges) for f in ed.link_faces})


def duplicate_face_translate_scale(bm, face, position, scale, scale_center):
    """Duplicate a face and transform it
    """
    ret = bmesh.ops.duplicate(bm, geom=[face])
    verts = filter_geom(ret["geom"], BMVert)

    bmesh.ops.scale(bm, verts=verts, vec=scale, space=Matrix.Translation(-scale_center))
    bmesh.ops.translate(bm, verts=verts, vec=position)
    return ret


def extrude_edges_to_depth(bm, edges, depth):
    """Extrude edges only and translate
    """
    ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
    bmesh.ops.translate(bm, verts=filter_geom(ext["geom"], BMVert), vec=depth)


def extrude_faces_add_slope(bm, faces, extrude_normal, extrude_depth):
    """Extrude faces and move top edge back to form a wedge
    """
    res = bmesh.ops.extrude_discrete_faces(bm, faces=faces)
    bmesh.ops.translate(
        bm,
        vec=extrude_normal * extrude_depth,
        verts=list({v for face in res["faces"] for v in face.verts}),
    )

    for face in res["faces"]:
        top_edge = max(
            filter_horizontal_edges(face.edges, face.normal),
            key=lambda e: calc_edge_median(e).z,
        )
        bmesh.ops.translate(bm, vec=-face.normal * extrude_depth, verts=top_edge.verts)


def subdivide_face_into_vertical_segments(bm, face, segments):
    """Cut a face(quad) vertically into multiple faces
    """
    res = bmesh.ops.subdivide_edges(
        bm, edges=filter_vertical_edges(face.edges, face.normal), cuts=segments
    ).get("geom_inner")

    return list({f for e in filter_geom(res, BMEdge) for f in e.link_faces})


def double_and_make_even(value):
    """multiply a number by 2 and make it even
    """
    double = value * 2
    return double if double % 2 == 0 else double + 1


def create_bar_from_face(bm, face, median, position, scale, depth, vertical=False):
    """Create bar geometry from a face
    """
    dup = duplicate_face_translate_scale(bm, face, position, scale, median).get("geom")
    edges = [filter_horizontal_edges, filter_vertical_edges][vertical](
        filter_geom(dup, BMEdge), face.normal
    )
    extrude_edges_to_depth(bm, edges, depth)

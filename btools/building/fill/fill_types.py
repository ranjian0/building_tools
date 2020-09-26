from enum import Enum, auto

import bmesh
from bmesh.types import BMEdge, BMVert
from mathutils import Vector, Matrix

from ...utils import (
    VEC_UP,
    FaceMap,
    validate,
    local_xyz,
    filter_geom,
    map_new_faces,
    add_faces_to_map,
    calc_edge_median,
    calc_face_dimensions,
    filter_vertical_edges,
    filter_horizontal_edges,
    add_facemap_for_groups,
    valid_ngon,
    ngon_to_quad,
)


class FillUser(Enum):
    DOOR = auto()
    WINDOW = auto()


def add_fill(bm, faces, prop):
    """Add fills
    """
    for face in faces:
        face.select = False
        if not valid_ngon(face):
            ngon_to_quad(bm, face)
        fill_face(bm, face, prop, prop.comp)
    return True


def fill_face(bm, face, prop, dw="DOOR"):
    """Fill face"""
    validate_fill_props(prop)
    user = FillUser.DOOR if dw=="DOOR" else FillUser.WINDOW
    if prop.fill_type == "PANELS":
        add_facemap_for_groups(FaceMap.DOOR_PANELS)
        fill_panel(bm, face, prop.panel_fill)
    elif prop.fill_type == "GLASS_PANES":
        add_facemap_for_groups(FaceMap.DOOR_PANES if dw=="DOOR" else FaceMap.WINDOW_PANES)
        fill_glass_panes(bm, face, prop.glass_fill, user)
    elif prop.fill_type == "LOUVER":
        add_facemap_for_groups(FaceMap.DOOR_LOUVERS if dw=="DOOR" else FaceMap.WINDOW_LOUVERS)
        fill_louver(bm, face, prop.louver_fill, user)
    elif prop.fill_type == "BAR":
        add_facemap_for_groups(FaceMap.WINDOW_BARS)
        fill_bar(bm, face, prop.bar_fill)


def validate_fill_props(prop):
    if prop.fill_type == "LOUVER":
        # XXX keep louver depth less than window depth
        fill = prop.louver_fill
        depth = getattr(prop, "door_depth", getattr(prop, "window_depth", getattr(prop, "dw_depth", 1e10)))
        fill.louver_depth = min(fill.louver_depth, depth)
    elif prop.fill_type == "BAR":
        # XXX keep bar depth smaller than window depth
        fill = prop.bar_fill
        depth = getattr(prop, "door_depth", getattr(prop, "window_depth", getattr(prop, "dw_depth", 1e10)))
        fill.bar_depth = min(fill.bar_depth, depth)
    elif prop.fill_type == "LOUVER":
        # XXX keep louver depth less than window depth
        fill = prop.louver_fill
        depth = getattr(prop, "door_depth", getattr(prop, "window_depth", getattr(prop, "dw_depth", 1e10)))
        fill.louver_depth = min(fill.louver_depth, depth)


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

    xyz = local_xyz(face)
    face_center = face.calc_center_median()
    width, height = calc_face_dimensions(face)

    # XXX bar width should not exceed window size
    min_dimension = min(
        [width / max(prop.bar_count_x, 1), height / max(prop.bar_count_y, 1)]
    )
    prop.bar_width = min(prop.bar_width, min_dimension)

    # -- transform vars
    transform_space = (
        Matrix.Rotation(-VEC_UP.angle(xyz[1]), 4, xyz[0]) @ Matrix.Translation(-face_center)
    )

    # -- horizontal
    depth = face.normal * prop.bar_depth
    offset = height / (prop.bar_count_x + 1)
    for i in range(prop.bar_count_x):
        item_off = Vector((0, 0, -height / 2 + (i + 1) * offset))
        transform = (
            Matrix.Translation(depth + item_off) @
            Matrix.Scale(prop.bar_width / height, 4, VEC_UP)
        )
        create_bar_from_face(bm, face, transform, transform_space, -depth)

    # -- vertical
    eps = 0.015
    offset = width / (prop.bar_count_y + 1)
    depth = face.normal * (prop.bar_depth - eps)
    for i in range(prop.bar_count_y):
        item_off = xyz[0] * (-width / 2 + ((i + 1) * offset))
        transform = (
            Matrix.Translation(depth + item_off) @
            Matrix.Scale(prop.bar_width / width, 4, xyz[0])
        )
        create_bar_from_face(bm, face, transform, transform_space, -depth, True)


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
    v_edges = filter_vertical_edges(face.edges)
    h_edges = filter_horizontal_edges(face.edges)

    edges = []
    if cuts_x > 0:
        res = bmesh.ops.subdivide_edges(bm, edges=v_edges, cuts=cuts_x)
        edges.extend(filter_geom(res["geom_inner"], BMEdge))

    if cuts_y > 0:
        res = bmesh.ops.subdivide_edges(bm, edges=h_edges + edges, cuts=cuts_y)
        edges.extend(filter_geom(res["geom_inner"], BMEdge))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
    return list({f for ed in validate(edges) for f in ed.link_faces})


def create_bar_from_face(bm, face, trans, trans_space, depth, vertical=False):
    """Create bar geometry from a face
    """
    dup = duplicate_face_translate_scale(bm, face, trans, trans_space).get("geom")
    edges = [filter_horizontal_edges, filter_vertical_edges][vertical](
        filter_geom(dup, BMEdge)
    )
    extrude_edges_to_depth(bm, edges, depth)


def duplicate_face_translate_scale(bm, face, trans, trans_space):
    """Duplicate a face and transform it
    """
    ret = bmesh.ops.duplicate(bm, geom=[face])
    verts = filter_geom(ret["geom"], BMVert)
    bmesh.ops.transform(bm, verts=verts, matrix=trans, space=trans_space)
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
            filter_horizontal_edges(face.edges),
            key=lambda e: calc_edge_median(e).z,
        )
        bmesh.ops.translate(bm, vec=-face.normal * extrude_depth, verts=top_edge.verts)


def subdivide_face_into_vertical_segments(bm, face, segments):
    """Cut a face(quad) vertically into multiple faces
    """
    res = bmesh.ops.subdivide_edges(
        bm, edges=filter_vertical_edges(face.edges), cuts=segments
    ).get("geom_inner")

    return list({f for e in filter_geom(res, BMEdge) for f in e.link_faces})


def double_and_make_even(value):
    """multiply a number by 2 and make it even
    """
    double = value * 2
    return double if double % 2 == 0 else double + 1

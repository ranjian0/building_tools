import bmesh
from mathutils import Vector, Matrix
from bmesh.types import BMEdge, BMVert
from ...utils import (
    filter_geom,
    calc_edge_median,
    calc_face_dimensions,
    filter_vertical_edges,
    filter_horizontal_edges,
)


def fill_panel(bm, face, prop):
    """Create panels on face

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        face (bmesh.types.BMFace): face to create panels on
        prop (bpy.types.PropertyGroup): FillPanel
    """
    if prop.panel_count_x + prop.panel_count_y == 0:
        return

    bmesh.ops.inset_individual(bm, faces=[face], thickness=prop.panel_border_size)
    quads = subdivide_face_into_quads(bm, face, prop.panel_count_x, prop.panel_count_y)
    bmesh.ops.inset_individual(bm, faces=quads, thickness=prop.panel_margin / 2)
    bmesh.ops.translate(
        bm,
        verts=list({v for f in quads for v in f.verts}),
        vec=face.normal * prop.panel_depth,
    )


def fill_glass_panes(bm, face, prop):
    """Create glass panes on face

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        face (bmesh.types.BMFace): face to create glass panes on
        prop (bpy.types.PropertyGroup): FillGlassPanes
    """
    if prop.pane_count_x + prop.pane_count_y == 0:
        return

    quads = subdivide_face_into_quads(bm, face, prop.pane_count_x, prop.pane_count_y)
    bmesh.ops.inset_individual(bm, faces=quads, thickness=prop.pane_margin)
    for f in quads:
        bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * prop.pane_depth)


def fill_bar(bm, face, prop):
    """Create bars on face

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        face (bmesh.types.BMFace): face to create panels on
        prop (bpy.types.PropertyGroup): FillBars
    """

    width, height = calc_face_dimensions(face)
    face_center = face.calc_center_median()

    # -- horizontal
    offset = height / (prop.bar_count_x + 1)
    for i in range(prop.bar_count_x):
        scale = (1, 1, prop.bar_width / height)
        position = Vector((face.normal * prop.bar_depth / 2)) + Vector(
            (0, 0, -height / 2 + (i + 1) * offset)
        )
        create_bar_from_face(bm, face, face_center, position, scale,
                             -face.normal * prop.bar_depth / 2)

    # -- vertical
    eps = 0.015
    offset = width / (prop.bar_count_y + 1)
    for i in range(prop.bar_count_y):
        scale = (prop.bar_width / width, prop.bar_width / width, 1)
        perp = face.normal.cross(Vector((0, 0, 1)))
        position = Vector((face.normal * ((prop.bar_depth / 2) - eps))) + perp * (
            -width / 2 + ((i + 1) * offset)
        )
        create_bar_from_face(bm, face, face_center, position, scale,
                             -face.normal * ((prop.bar_depth / 2) - eps), True)


def fill_louver(bm, face, prop):
    """Create louvers from face

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        face (bmesh.types.BMFace): face to create louvers on
        prop (bpy.types.PropertyGroup): FillLouver
    """
    normal = face.normal
    if prop.louver_margin:
        bmesh.ops.inset_individual(bm, faces=[face], thickness=prop.louver_margin)

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

    extrude_faces_add_slope(bm, louver_faces, normal, prop.louver_depth)


def subdivide_face_into_quads(bm, face, cuts_x, cuts_y):
    """subdivide a face(quad) into more quads

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        face (bmesh.types.BMFace): face to operate on
        cuts_x (int): number of horizontal cuts
        cuts_y (int): number of vertical cuts

    Returns:
        list(bmesh.types.BMFace): new faces from subdivision
    """
    v_edges = filter_vertical_edges(face.edges, face.normal)
    h_edges = filter_horizontal_edges(face.edges, face.normal)

    edges = []
    if cuts_x > 0:
        res = bmesh.ops.subdivide_edges(bm, edges=v_edges, cuts=cuts_x).get(
            "geom_inner"
        )
        edges.extend(filter_geom(res, BMEdge))

    if cuts_y > 0:
        res = bmesh.ops.subdivide_edges(bm, edges=h_edges + edges, cuts=cuts_y).get(
            "geom_inner"
        )
        edges.extend(filter_geom(res, BMEdge))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
    return list({f for ed in edges for f in ed.link_faces})


def duplicate_face_translate_scale(bm, face, position, scale, scale_center):
    """Duplicate a face and transform it

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        face (bmesh.types.BMFace): face to duplicate
        position (vector): position of duplicate face
        scale (tuple): scale of duplicate face
        scale_center (vector): center of scaling operation

    Returns:
        dict geometry of duplicate face
    """
    ret = bmesh.ops.duplicate(bm, geom=[face])
    verts = filter_geom(ret["geom"], BMVert)

    bmesh.ops.scale(bm, verts=verts, vec=scale, space=Matrix.Translation(-scale_center))
    bmesh.ops.translate(bm, verts=verts, vec=position)
    return ret


def extrude_edges_to_depth(bm, edges, depth):
    """Extrude edges only

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        edges (list): edges to extrude
        depth (float): depth to extrude to
    """
    ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
    bmesh.ops.translate(bm, verts=filter_geom(ext["geom"], BMVert), vec=depth)


def extrude_faces_add_slope(bm, faces, extrude_normal, extrude_depth):
    """Extrude faces and move top edge back to form wedge.slope

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        faces (list): faces to extrude
        extrude_normal (vector): direction of extrusion
        extrude_depth (float): magnitude of extrusion
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
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)


def subdivide_face_into_vertical_segments(bm, face, segments):
    """Cut a face(quad) vertically into multiple faces

    Args:
        bm (bmesh.types.BMesh): bmesh of editmode object
        face (bmesh.types.BMFace): face to operate on
        segments (int): number of segments

    Returns:
        list: face segmets formed from subdivision
    """
    res = bmesh.ops.subdivide_edges(
        bm, edges=filter_vertical_edges(face.edges, face.normal), cuts=segments
    ).get("geom_inner")

    return list({f for e in filter_geom(res, BMEdge) for f in e.link_faces})


def double_and_make_even(value):
    """multiply a number by 2 and make it even

    Args:
        value (int): value to operator on

    Returns:
        int: result after doubling and making even
    """
    double = value * 2
    return double if double % 2 == 0 else double + 1


def create_bar_from_face(bm, face, face_median, bar_position, bar_scale, bar_depth,
                         vertical=False):

    duplicate = duplicate_face_translate_scale(
        bm, face, bar_position, bar_scale, face_median
    ).get("geom")
    edges = (
        filter_vertical_edges(filter_geom(duplicate, BMEdge), face.normal)
        if vertical else
        filter_horizontal_edges(filter_geom(duplicate, BMEdge), face.normal)
    )
    extrude_edges_to_depth(bm, edges, bar_depth,)

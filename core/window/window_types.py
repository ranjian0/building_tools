import bmesh
from ..fill import fill_bar, fill_louver, fill_glass_panes, FillUser
from ...utils import (
    FaceMap,
    arc_edge,
    filter_geom,
    map_new_faces,
    add_faces_to_map,
    calc_edge_median,
    add_facemap_for_groups,
    create_cube_without_faces,
    inset_face_with_scale_offset,
    subdivide_face_edges_vertical,
    get_width_and_height,
    local_to_global
)

from mathutils import Vector


def create_window(bm, faces, prop):
    """Generate a window
    """
    for face in faces:
        array_faces = create_window_array(bm, face, prop.array)

        for aface in array_faces:
            face = create_window_split(bm, aface, prop.size_offset)
            if not face:
                continue

            face = create_window_frame(bm, face, prop)
            create_window_fill(bm, face, prop)


@map_new_faces(FaceMap.WALLS)
def create_window_split(bm, face, prop):
    """Use properties from SplitOffset to subdivide face into regular quads
    """
    wall_w, wall_h = get_width_and_height(face)
    scale_x = prop.size.x/wall_w
    scale_y = prop.size.y/wall_h
    offset = local_to_global(face, Vector((prop.offset.x, prop.offset.y, 0.0)))
    return inset_face_with_scale_offset(bm, face, scale_y, scale_x, offset.x, offset.y, offset.z)


def create_window_array(bm, face, prop):
    """Use ArrayProperty to subdivide face vertically
    """
    if prop.count <= 1:
        return [face]
    res = subdivide_face_edges_vertical(bm, face, prop.count - 1)
    inner_edges = filter_geom(res["geom_inner"], bmesh.types.BMEdge)
    return list({f for e in inner_edges for f in e.link_faces})


@map_new_faces(FaceMap.WINDOW_FRAMES, skip=FaceMap.WINDOW)
def create_window_frame(bm, face, prop):
    """Create extrude and inset around a face to make window frame
    """
    if prop.has_arch():
        return create_window_frame_arched(bm, face, prop)

    faces = None
    normal = face.normal.copy()
    if prop.frame_thickness > 0.0:
        res = bmesh.ops.inset_individual(
            bm, faces=[face], thickness=prop.frame_thickness, use_even_offset=True
        )
        faces = res.get("faces")

    if prop.window_depth > 0.0:
        face = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces").pop()
        bmesh.ops.translate(bm, verts=face.verts, vec=-normal * prop.window_depth)

    if faces and prop.frame_depth > 0.0:
        geom = bmesh.ops.extrude_face_region(bm, geom=faces).get("geom")
        verts = filter_geom(geom, bmesh.types.BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=normal * prop.frame_depth)

    add_faces_to_map(bm, [face], FaceMap.WINDOW)
    return face


def create_window_frame_arched(bm, face, prop):
    """ Arch the top edge of face then extrude and make window frame
    """
    arch = prop.arch
    top = sorted(face.edges, key=lambda ed: calc_edge_median(ed).z).pop()
    arc_edge(bm, top, arch.resolution, arch.height, arch.offset, arch.function)

    frame_faces = []
    normal = face.normal.copy()
    if prop.frame_thickness > 0.0:
        res = bmesh.ops.inset_individual(
            bm, faces=[face], thickness=prop.frame_thickness, use_even_offset=True
        )
        frame_faces = res.get("faces")

    verts = sorted(face.verts, key=lambda v: v.co.z)
    edge = bmesh.ops.connect_verts(bm, verts=verts[2:4]).get("edges").pop()

    fcs = extrude_window_and_frame_depth(bm, edge.link_faces, frame_faces, normal, prop)
    if fcs:
        add_faces_to_map(bm, fcs, FaceMap.WINDOW)
        return sorted(fcs, key=lambda f: f.calc_center_median().z)[0]
    return min(edge.link_faces, key=lambda f: f.calc_center_median().z)


def create_window_fill(bm, face, prop):
    """Create extra elements on face
    """

    if prop.fill_type == "GLASS PANES":
        add_facemap_for_groups(FaceMap.WINDOW_PANES)
        if prop.has_arch():
            pane_arch_face(bm, face, prop.glass_fill)
        fill_glass_panes(bm, face, prop.glass_fill, user=FillUser.WINDOW)
    elif prop.fill_type == "BAR":
        add_facemap_for_groups(FaceMap.WINDOW_BARS)
        fill_bar(bm, face, prop.bar_fill)
        if prop.has_arch():
            add_extra_arch_bar(bm, face, prop.bar_fill)
    elif prop.fill_type == "LOUVER":
        add_facemap_for_groups(FaceMap.WINDOW_LOUVERS)
        fill_louver(bm, face, prop.louver_fill, user=FillUser.WINDOW)


def extrude_window_and_frame_depth(bm, window_faces, frame_faces, normal, prop):
    faces = None
    if prop.window_depth > 0.0:
        res = bmesh.ops.extrude_face_region(bm, geom=window_faces).get("geom")
        bmesh.ops.delete(bm, geom=window_faces, context="FACES")
        faces = filter_geom(res, bmesh.types.BMFace)
        verts = list({v for f in faces for v in f.verts})
        bmesh.ops.translate(bm, verts=verts, vec=-normal * prop.window_depth)

    if frame_faces and prop.frame_depth > 0.0:
        geom = bmesh.ops.extrude_face_region(bm, geom=frame_faces).get("geom")
        verts = filter_geom(geom, bmesh.types.BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=normal * prop.frame_depth)

    return faces


@map_new_faces(FaceMap.WINDOW_BARS)
def add_extra_arch_bar(bm, face, prop):
    top_edge = sorted(face.edges, key=lambda ed: calc_edge_median(ed).z).pop()
    bar_pos = calc_edge_median(top_edge) + (face.normal * prop.bar_depth / 4)
    if face.normal.y:
        bar_size = (top_edge.calc_length(), prop.bar_depth / 2, prop.bar_width)
        back_face = "back" if face.normal.y > 0 else "front"
        face_flags = {"left": True, "right": True, back_face: True}
    else:
        bar_size = (prop.bar_depth / 2, top_edge.calc_length(), prop.bar_width)
        back_face = "right" if face.normal.x > 0 else "left"
        face_flags = {"front": True, "back": True, back_face: True}

    create_cube_without_faces(bm, bar_size, bar_pos, **face_flags)


@map_new_faces(FaceMap.WINDOW_PANES)
def pane_arch_face(bm, face, prop):
    edge = sorted(face.edges, key=lambda ed: calc_edge_median(ed).z).pop()
    arch_face = sorted(edge.link_faces, key=lambda f: f.calc_center_median().z).pop()
    add_faces_to_map(bm, [arch_face], FaceMap.WINDOW)
    bmesh.ops.inset_individual(
        bm, faces=[arch_face], thickness=prop.pane_margin * 0.75, use_even_offset=True
    )
    bmesh.ops.translate(
        bm, verts=arch_face.verts, vec=-arch_face.normal * prop.pane_depth
    )

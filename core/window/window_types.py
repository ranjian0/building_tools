import bmesh
from ..fill import fill_bar, fill_louver, fill_glass_panes
from ...utils import (
    arc_edge,
    filter_geom,
    calc_edge_median,
    create_cube_without_faces,
    inset_face_with_scale_offset,
    subdivide_face_edges_vertical,
)


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


def create_window_split(bm, face, prop):
    """Use properties from SplitOffset to subdivide face into regular quads
    """
    size, off = prop.size, prop.offset
    return inset_face_with_scale_offset(bm, face, size.y, size.x, off.x, off.y, off.z)


def create_window_array(bm, face, prop):
    """Use ArrayProperty to subdivide face vertically
    """
    if prop.count <= 1:
        return [face]
    res = subdivide_face_edges_vertical(bm, face, prop.count - 1)
    inner_edges = filter_geom(res["geom_inner"], bmesh.types.BMEdge)
    return list({f for e in inner_edges for f in e.link_faces})


def create_window_frame(bm, face, prop):
    """Create extrude and inset around a face to make window frame
    """
    if prop.has_arch():
        return create_window_frame_arched(bm, face, prop)

    faces = None
    normal = face.normal.copy()
    if prop.frame_thickness > 0.0:
        res = bmesh.ops.inset_individual(
            bm, faces=[face], thickness=prop.frame_thickness,
            use_even_offset=True
        )
        faces = res.get('faces')

    if prop.window_depth > 0.0:
        face = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces")[-1]
        bmesh.ops.translate(bm, verts=face.verts, vec=-normal * prop.window_depth)

    if faces and prop.frame_depth > 0.0:
        geom = bmesh.ops.extrude_face_region(bm, geom=faces).get("geom")
        verts = filter_geom(geom, bmesh.types.BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=normal * prop.frame_depth)

    return face


def create_window_frame_arched(bm, face, prop):
    """ Arch the top edge of face then extrude and inset around a face to make window frame
    """
    top = sorted([e for e in face.edges], key=lambda ed: calc_edge_median(ed).z)[-1]
    arc_edge(bm, top, prop.arch.resolution, prop.arch.height, prop.arch.offset)

    faces = []
    normal = face.normal.copy()
    if prop.frame_thickness > 0.0:
        res = bmesh.ops.inset_individual(
            bm, faces=[face], thickness=prop.frame_thickness, use_even_offset=True
        )
        frame_faces = res.get('faces')

    verts = sorted(face.verts, key=lambda v: v.co.z)
    edge = bmesh.ops.connect_verts(bm, verts=verts[2:4]).get('edges')[-1]
    faces = edge.link_faces

    if prop.window_depth > 0.0:
        res = bmesh.ops.extrude_face_region(
            bm, geom=faces).get("geom")
        bmesh.ops.delete(bm, geom=faces, context='FACES')
        faces = filter_geom(res, bmesh.types.BMFace)
        verts = list({v for f in faces for v in f.verts})
        bmesh.ops.translate(bm, verts=verts, vec=-normal * prop.window_depth)

    if frame_faces and prop.frame_depth > 0.0:
        geom = bmesh.ops.extrude_face_region(bm, geom=frame_faces).get("geom")
        verts = filter_geom(geom, bmesh.types.BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=normal * prop.frame_depth)

    return sorted(faces, key=lambda f: f.calc_center_median().z)[0]


def create_window_fill(bm, face, prop):
    """Create extra elements on face
    """

    if prop.fill_type == "NONE":
        pass
    elif prop.fill_type == "GLASS PANES":
        fill_glass_panes(bm, face, prop.glass_fill)
    elif prop.fill_type == "BAR":
        fill_bar(bm, face, prop.bar_fill)
        if prop.has_arch():
            add_extra_arch_bar(bm, face, prop.bar_fill)
    elif prop.fill_type == "LOUVER":
        fill_louver(bm, face, prop.louver_fill)


def add_extra_arch_bar(bm, face, prop):
    top_edge = sorted(face.edges, key=lambda ed: calc_edge_median(ed).z)[-1]
    bar_pos = calc_edge_median(top_edge) + (face.normal * prop.bar_depth/4)
    if face.normal.y:
        bar_size = (top_edge.calc_length(), prop.bar_depth/2, prop.bar_width)
        back_face = 'back' if face.normal.y > 0 else 'front'
        face_flags = {'left': True, 'right': True, back_face: True}
    else:
        bar_size = (prop.bar_depth/2, top_edge.calc_length(), prop.bar_width)
        back_face = 'right' if face.normal.x > 0 else 'left'
        face_flags = {'front': True, 'back': True, back_face: True}

    create_cube_without_faces(bm, bar_size, bar_pos, **face_flags)

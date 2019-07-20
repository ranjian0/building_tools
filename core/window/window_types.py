import bmesh
from ...utils import split, filter_geom, split_quad
from ..fill import fill_bar, fill_louver, fill_glass_panes


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
    return split(bm, face, size.y, size.x, off.x, off.y, off.z)


def create_window_array(bm, face, prop):
    """Use ArrayProperty to subdivide face horizontally/vertically for
    further processing
    """
    if prop.count <= 1 or not prop.show_props:
        return [face]
    res = split_quad(bm, face, not prop.direction == "VERTICAL", prop.count - 1)
    inner_edges = filter_geom(res["geom_inner"], bmesh.types.BMEdge)
    return list({f for e in inner_edges for f in e.link_faces})


def create_window_frame(bm, face, prop):
    """Create extrude and inset around a face to make window frame
    """

    normal = face.normal
    if prop.frame_thickness > 0.0:
        res = bmesh.ops.inset_individual(
            bm, faces=[face], thickness=prop.frame_thickness
        )
        faces = res.get("faces")

    if prop.window_depth > 0.0:
        face = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces")[-1]
        bmesh.ops.translate(bm, verts=face.verts, vec=-normal * prop.window_depth)

    if prop.frame_depth > 0.0:
        geom = bmesh.ops.extrude_face_region(bm, geom=faces).get("geom")
        verts = filter_geom(geom, bmesh.types.BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=normal * prop.frame_depth)

    return face


def create_window_fill(bm, face, prop):
    """Create extra elements on face
    """

    if prop.fill_type == "NONE":
        pass
    elif prop.fill_type == "GLASS PANES":
        fill_glass_panes(bm, face, prop.glass_fill)
    elif prop.fill_type == "BAR":
        fill_bar(bm, face, prop.bar_fill)
    elif prop.fill_type == "LOUVER":
        fill_louver(bm, face, prop.louver_fill)

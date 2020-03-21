import bmesh
from ..fill import fill_bar, fill_louver, fill_glass_panes, FillUser
from ..common.frame import (
    add_frame_depth,
)
from ..common.arch import (
    fill_arch,
    create_arch,
    add_arch_depth,
)
from ...utils import (
    FaceMap,
    is_ngon,
    popup_message,
    map_new_faces,
    add_faces_to_map,
    add_facemap_for_groups,
    calc_face_dimensions,
    subdivide_face_horizontally,
    subdivide_face_vertically,
    get_top_edges,
    get_top_faces,
    get_bottom_faces,
    local_xyz,
)


def create_window(bm, faces, prop):
    """Generate a window
    """
    for face in faces:
        if is_ngon(face):
            popup_message("Window creation not supported for n-gon", "Ngon Error")
            return False

        face.select = False

        array_faces = subdivide_face_horizontally(bm, face, widths=[prop.size_offset.size.x]*prop.count)
        for aface in array_faces:
            face = create_window_split(bm, aface, prop.size_offset.size, prop.size_offset.offset)
            window, arch = create_window_frame(bm, face, prop)
            fill_window_face(bm, window, prop)
            if prop.add_arch:
                fill_arch(bm, arch, prop)
    return True


@map_new_faces(FaceMap.WALLS)
def create_window_split(bm, face, size, offset):
    """Use properties from SplitOffset to subdivide face into regular quads
    """
    wall_w, wall_h = calc_face_dimensions(face)
    # horizontal split
    h_widths = [wall_w/2 + offset.x - size.x/2, size.x, wall_w/2 - offset.x - size.x/2]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical split
    v_width = [wall_h/2 - offset.y - size.y/2, size.y, wall_h/2 + offset.y - size.y/2]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_width)

    return v_faces[1]


@map_new_faces(FaceMap.WINDOW_FRAMES, skip=FaceMap.WINDOW)
def create_window_frame(bm, face, prop):
    """Create extrude and inset around a face to make window frame
    """

    normal = face.normal.copy()

    window_face, frame_faces = make_window_inset(bm, face, prop.size_offset.size, prop.frame_thickness)
    arch_face = None

    if prop.add_arch:
        frame_faces.remove(get_top_faces(frame_faces).pop()) # remove top face from frame_faces
        top_edges = get_top_edges({e for f in get_bottom_faces(frame_faces, n=3)[1:] for e in f.edges}, n=2)
        arch_face, arch_frame_faces = create_arch(bm, top_edges, frame_faces, prop.arch, prop.frame_thickness, local_xyz(face))
        frame_faces += arch_frame_faces
        arch_face = add_arch_depth(bm, arch_face, prop.arch.depth, normal)

    window_face = add_window_depth(bm, window_face, prop.window_depth, normal)

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if frame_faces:
        add_frame_depth(bm, frame_faces, prop.frame_depth, normal)

    add_faces_to_map(bm, [window_face], FaceMap.WINDOW)
    return window_face, arch_face


def add_window_depth(bm, window, depth, normal):
    if depth > 0.0:
        window = bmesh.ops.extrude_discrete_faces(bm, faces=[window]).get("faces").pop()
        bmesh.ops.translate(bm, verts=window.verts, vec=-normal * depth)
        return window
    else:
        return window


def make_window_inset(bm, face, size, frame_thickness):
    """ Make two horizontal cuts and two vertical cuts
    """
    if frame_thickness > 0:
        window_width = size.x - frame_thickness * 2
        window_height = size.y - frame_thickness * 2
        # horizontal cuts
        h_widths = [frame_thickness, window_width, frame_thickness]
        h_faces = subdivide_face_horizontally(bm, face, h_widths)
        # vertical cuts
        v_widths = [frame_thickness, window_height, frame_thickness]
        v_faces = subdivide_face_vertically(bm, h_faces[1], v_widths)
        return v_faces[1], h_faces[::2] + v_faces[::2]
    else:
        return face, []


def fill_window_face(bm, face, prop):
    """Create extra elements on face
    """
    if prop.fill_type == "GLASS_PANES":
        add_facemap_for_groups(FaceMap.WINDOW_PANES)
        fill_glass_panes(bm, face, prop.glass_fill, user=FillUser.WINDOW)
    elif prop.fill_type == "BAR":
        add_facemap_for_groups(FaceMap.WINDOW_BARS)
        fill_bar(bm, face, prop.bar_fill)
    elif prop.fill_type == "LOUVER":
        add_facemap_for_groups(FaceMap.WINDOW_LOUVERS)
        fill_louver(bm, face, prop.louver_fill, user=FillUser.WINDOW)

import bmesh

from ..generic import clamp_count
from ..frame import add_frame_depth
from ..fill import fill_bar, fill_louver, fill_glass_panes, FillUser

from ..arch import fill_arch, create_arch, add_arch_depth
from ...utils import (
    clamp,
    FaceMap,
    validate,
    local_xyz,
    valid_ngon,
    popup_message,
    get_top_edges,
    get_top_faces,
    map_new_faces,
    get_bottom_faces,
    add_faces_to_map,
    extrude_face_region,
    calc_face_dimensions,
    add_facemap_for_groups,
    subdivide_face_vertically,
    subdivide_face_horizontally,
)


def create_window(bm, faces, prop):
    """Generate a window
    """
    for face in faces:
        if not valid_ngon(face):
            popup_message("Window creation not supported for non-rectangular n-gon", "Ngon Error")
            return False

        face.select = False
        clamp_count(calc_face_dimensions(face)[0], prop.frame_thickness * 2, prop)
        array_faces = subdivide_face_horizontally(bm, face, widths=[prop.size_offset.size.x]*prop.count)
        for aface in array_faces:
            face = create_window_split(bm, aface, prop.size_offset.size, prop.size_offset.offset)
            window, arch = create_window_frame(bm, face, prop)
            fill_window_face(bm, window, prop)
            if prop.add_arch:
                fill_arch(bm, arch, prop)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
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
    v_width = [wall_h/2 + offset.y - size.y/2, size.y, wall_h/2 - offset.y - size.y/2]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_width)

    return v_faces[1]


def create_window_frame(bm, face, prop):
    """Create extrude and inset around a face to make window frame
    """

    normal = face.normal.copy()

    # XXX Frame thickness should not exceed size of window
    min_frame_size = min(calc_face_dimensions(face)) / 2
    prop.frame_thickness = clamp(prop.frame_thickness, 0.01, min_frame_size - 0.001)

    window_face, frame_faces = make_window_inset(bm, face, prop.size_offset.size, prop.frame_thickness)
    arch_face = None

    # create arch
    if prop.add_arch:
        frame_faces.remove(get_top_faces(frame_faces).pop()) # remove top face from frame_faces
        top_edges = get_top_edges({e for f in get_bottom_faces(frame_faces, n=3)[1:] for e in f.edges}, n=2)
        arch_face, arch_frame_faces = create_arch(bm, top_edges, frame_faces, prop.arch, prop.frame_thickness, local_xyz(face))
        frame_faces += arch_frame_faces

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    # add depths
    if prop.add_arch:
        _, [window_face], [arch_face], frame_faces = add_frame_depth(bm, [], [window_face], [arch_face], frame_faces, prop.frame_depth, normal)
        arch_face, new_frame_faces = add_arch_depth(bm, arch_face, prop.arch.depth, normal)
        frame_faces += new_frame_faces
    else:
        _, [window_face], _, frame_faces = add_frame_depth(bm, [], [window_face], [], frame_faces, prop.frame_depth, normal)

    window_face, new_frame_faces = add_window_depth(bm, window_face, prop.window_depth, normal)
    frame_faces += new_frame_faces

    # add face maps
    add_faces_to_map(bm, [window_face], FaceMap.WINDOW)
    add_faces_to_map(bm, validate(frame_faces), FaceMap.FRAME)
    if prop.add_arch:
        add_faces_to_map(bm, [arch_face], FaceMap.WINDOW)

    return window_face, arch_face


def add_window_depth(bm, window, depth, normal):
    if depth > 0.0:
        window_faces, frame_faces = extrude_face_region(bm, [window], -depth, normal)
        return window_faces[0], frame_faces
    else:
        return window, []


def make_window_inset(bm, face, size, frame_thickness):
    """ Make two horizontal cuts and two vertical cuts
    """
    window_width = size.x - frame_thickness * 2
    window_height = size.y - frame_thickness * 2
    # horizontal cuts
    h_widths = [frame_thickness, window_width, frame_thickness]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical cuts
    v_widths = [frame_thickness, window_height, frame_thickness]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_widths)
    return v_faces[1], h_faces[::2] + v_faces[::2]


def fill_window_face(bm, face, prop):
    """Create extra elements on face
    """
    validate_fill_props(prop)
    if prop.fill_type == "GLASS_PANES":
        add_facemap_for_groups(FaceMap.WINDOW_PANES)
        fill_glass_panes(bm, face, prop.glass_fill, user=FillUser.WINDOW)
    elif prop.fill_type == "BAR":
        add_facemap_for_groups(FaceMap.WINDOW_BARS)
        fill_bar(bm, face, prop.bar_fill)
    elif prop.fill_type == "LOUVER":
        add_facemap_for_groups(FaceMap.WINDOW_LOUVERS)
        fill_louver(bm, face, prop.louver_fill, user=FillUser.WINDOW)


def validate_fill_props(prop):
    if prop.fill_type == "BAR":
        # XXX keep bar depth smaller than window depth
        fill = prop.bar_fill
        fill.bar_depth = min(fill.bar_depth, prop.window_depth)
    elif prop.fill_type == "LOUVER":
        # XXX keep louver depth less than window depth
        fill = prop.louver_fill
        depth = getattr(prop, "door_depth", getattr(prop, "dw_depth", 1e10))
        fill.louver_depth = min(fill.louver_depth, depth)

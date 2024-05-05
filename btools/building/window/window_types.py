import bmesh

from ...utils import (
    XYDir,
    arc_edge,
    calc_edge_median,
    calc_face_dimensions,
    clamp,
    extrude_face,
    extrude_face_region,
    filter_horizontal_edges,
    filter_vertical_edges,
    get_bottom_faces,
    get_top_edges,
    get_top_faces,
    local_xyz,
    ngon_to_quad,
    sort_edges,
    sort_faces,
    subdivide_face_horizontally,
    subdivide_face_vertically,
    valid_ngon,
    validate,
)
from ..arch import add_arch_depth, create_arch, fill_arch
from ..array import clamp_array_count, get_array_split_edges, spread_array
from ..fill import fill_face
from ..frame import add_frame_depth
from ..materialgroup import (
    MaterialGroup,
    add_faces_to_group,
    find_faces_without_matgroup,
    map_new_faces,
)


def create_window(bm, faces, prop):
    """Generate a window"""
    for face in faces:
        face.select_set(False)
        if not valid_ngon(face):
            ngon_to_quad(bm, face)

        clamp_array_count(face, prop)
        array_faces = subdivide_face_horizontally(
            bm, face, widths=[prop.width] * prop.count
        )
        max_width = calc_face_dimensions(array_faces[0])[0]

        split_edges = get_array_split_edges(array_faces)
        split_faces = [create_window_split(bm, aface, prop) for aface in array_faces]
        spread_array(bm, split_edges, split_faces, max_width, prop)

        for face in split_faces:
            window, arch = create_window_frame(bm, face, prop)
            if prop.type == "RECTANGULAR":
                fill_face(bm, window, prop, "WINDOW")
                if prop.add_arch:
                    fill_arch(bm, arch, prop)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

    nulfaces = find_faces_without_matgroup(bm)
    add_faces_to_group(bm, nulfaces, MaterialGroup.WALLS)
    return True


@map_new_faces(MaterialGroup.WALLS)
def create_window_split(bm, face, prop):
    """Use properties from SplitOffset to subdivide face into regular quads"""
    wall_w, wall_h = calc_face_dimensions(face)
    width, height, offset = *prop.size, prop.offset
    # horizontal split
    h_widths = [
        wall_w / 2 - offset.x - width / 2,
        width,
        wall_w / 2 + offset.x - width / 2,
    ]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical split
    v_width = [
        wall_h / 2 + offset.y - height / 2,
        height,
        wall_h / 2 - offset.y - height / 2,
    ]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_width)

    return v_faces[1]


def create_window_frame(bm, face, prop):
    """Create extrude and inset around a face to make window frame"""
    if prop.type == "CIRCULAR":
        return create_circular_frame(bm, face, prop)
    return create_rectangular_frame(bm, face, prop)


def create_circular_frame(bm, face, prop):
    """Create extrude and inset around circular face"""
    if prop.frame_depth != 0.0:
        face, _ = extrude_face(bm, face, -prop.frame_depth)

    xyz = local_xyz(face)
    width, length = calc_face_dimensions(face)
    prop.frame_thickness = min(prop.frame_thickness, min(length, width) / 2)

    # -- subdivide the face along the shortest side
    func = [subdivide_face_vertically, subdivide_face_horizontally][width > length]
    sections = [[length / 2] * 3, [width / 2] * 3][width > length]
    faces = func(bm, face, sections)

    # -- get edges that will be used to make circle
    mid = sort_faces(faces, xyz[0] if width > length else xyz[1])[1]
    func = [filter_horizontal_edges, filter_vertical_edges][width > length]
    edges = func(mid.edges)

    # -- move the edges towards each other
    median = mid.calc_center_median()
    end, start = sort_edges(edges, xyz[0] if width > length else xyz[1])
    for e in edges:
        bmesh.ops.translate(bm, verts=list(e.verts), vec=median - calc_edge_median(e))

    # -- arch the edges
    res = prop.resolution // 2
    radius = min(length, width) / 2
    arc_edge(bm, start, res, radius, xyz)
    arc_edge(bm, end, res, -radius, xyz)

    # -- inset for frame thicknes
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    res = bmesh.ops.inset_region(
        bm, faces=[mid], use_even_offset=True, thickness=prop.frame_thickness
    )

    # -- add window depth
    win, frames = add_window_depth(bm, mid, prop.window_depth, xyz[2])
    add_faces_to_group(bm, [win], MaterialGroup.WINDOW)
    add_faces_to_group(bm, res.get("faces", []) + frames, MaterialGroup.FRAME)
    return win, None


def create_rectangular_frame(bm, face, prop):
    """Create extrude and inset around a face to make rectangular window frame"""
    normal = face.normal.copy()
    # XXX Frame thickness should not exceed size of window
    min_frame_size = min(calc_face_dimensions(face)) / 2
    prop.frame_thickness = clamp(prop.frame_thickness, 0.01, min_frame_size - 0.001)

    window_face, frame_faces = make_window_inset(bm, face, prop)
    arch_face = None

    # create arch
    if prop.add_arch:
        frame_faces.remove(
            get_top_faces(frame_faces).pop()
        )  # remove top face from frame_faces
        top_edges = get_top_edges(
            {e for f in get_bottom_faces(frame_faces, n=3)[1:] for e in f.edges}, n=2
        )
        arch_face, arch_frame_faces = create_arch(
            bm, top_edges, frame_faces, prop.arch, prop.frame_thickness, local_xyz(face)
        )
        frame_faces += arch_frame_faces

    else:
        # -- postprocess merge loose split verts
        merge_loose_split_verts(bm, window_face, prop)

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    # add depths
    if prop.add_arch:
        _, [window_face], [arch_face], frame_faces = add_frame_depth(
            bm, [], [window_face], [arch_face], frame_faces, prop.frame_depth, normal
        )
        arch_face, new_frame_faces = add_arch_depth(
            bm, arch_face, prop.arch.depth, normal
        )
        frame_faces += new_frame_faces
    else:
        _, [window_face], _, frame_faces = add_frame_depth(
            bm, [], [window_face], [], frame_faces, prop.frame_depth, normal
        )

    window_face, new_frame_faces = add_window_depth(
        bm, window_face, prop.window_depth, normal
    )
    frame_faces += new_frame_faces

    # add face maps
    add_faces_to_group(bm, [window_face], MaterialGroup.WINDOW)
    add_faces_to_group(bm, validate(frame_faces), MaterialGroup.FRAME)
    if prop.add_arch:
        add_faces_to_group(bm, [arch_face], MaterialGroup.WINDOW)

    return window_face, arch_face


def add_window_depth(bm, window, depth, normal):
    if depth > 0.0:
        window_faces, frame_faces = extrude_face_region(bm, [window], -depth, normal)
        return window_faces[0], frame_faces
    else:
        return window, []


def make_window_inset(bm, face, prop):
    """Make two horizontal cuts and two vertical cuts"""
    width, height, frame_thickness = *prop.size, prop.frame_thickness

    window_width = width - frame_thickness * 2
    window_height = height - frame_thickness * 2
    # horizontal cuts
    h_widths = [frame_thickness, window_width, frame_thickness]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical cuts
    v_widths = [frame_thickness, window_height, frame_thickness]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_widths)
    return v_faces[1], h_faces[::2] + v_faces[::2]


def merge_loose_split_verts(bm, window_face, prop):
    """Merge the split verts to the corners of the window frame"""
    median = window_face.calc_center_median()
    window_face_verts = [v for v in window_face.verts]
    for vert in window_face_verts:
        extent_edge = [e for e in vert.link_edges if e not in window_face.edges].pop()
        corner_vert = extent_edge.other_vert(vert)

        move_mag = prop.frame_thickness
        move_dir = XYDir(corner_vert.co - median)
        bmesh.ops.translate(bm, verts=[corner_vert], vec=move_dir * move_mag)

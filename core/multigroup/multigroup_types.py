import bmesh
from ..frame import (
    add_frame_depth,
)
from ..arch import (
    fill_arch,
    create_arch,
    add_arch_depth,
)
from ..door.door_types import (
    add_door_depth,
    create_door_fill,
)
from ..window.window_types import (
    fill_window_face,
)
from ...utils import (
    valid_ngon,
    FaceMap,
    popup_message,
    map_new_faces,
    add_faces_to_map,
    calc_face_dimensions,
    get_top_faces,
    get_top_edges,
    subdivide_face_horizontally,
    subdivide_face_vertically,
    local_xyz,
)


def create_multigroup(bm, faces, prop):
    """ Create multigroup from face selection
    """

    for face in faces:
        if not valid_ngon(face):
            popup_message("Multigroup creation not supported for non-rectangular n-gon!", "Ngon Error")
            return False

        face.select = False

        array_faces = subdivide_face_horizontally(bm, face, widths=[prop.size_offset.size.x]*prop.count)
        for aface in array_faces:
            face = create_multigroup_split(bm, aface, prop.size_offset.size, prop.size_offset.offset)
            doors, windows, arch = create_multigroup_frame(bm, face, prop)
            for door in doors:
                create_door_fill(bm, door, prop)
            for window in windows:
                fill_window_face(bm, window, prop)
            if prop.add_arch:
                fill_arch(bm, arch, prop)
    return True


@map_new_faces(FaceMap.WALLS)
def create_multigroup_split(bm, face, size, offset):
    """ Use properties from SizeOffset to subdivide face into regular quads
    """

    wall_w, wall_h = calc_face_dimensions(face)
    # horizontal split
    h_widths = [wall_w/2 + offset.x - size.x/2, size.x, wall_w/2 - offset.x - size.x/2]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical split
    v_width = [wall_h/2 + offset.y + size.y/2, wall_h/2 - offset.y - size.y/2]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_width)

    return v_faces[0]


def create_multigroup_frame(bm, face, prop):
    """ Extrude and inset face to make multigroup frame
    """
    normal = face.normal.copy()

    dws = parse_components(prop.components)
    door_faces, window_faces, frame_faces = make_multigroup_insets(bm, face, prop.size_offset.size, prop.frame_thickness, dws)
    arch_face = None

    # create arch
    if prop.add_arch:
        dw_count = count(dws)
        top_edges = get_top_edges({e for f in get_top_faces(frame_faces, n=2*dw_count+1)[-dw_count-1:] for e in f.edges}, n=dw_count+1)
        if dw_count == 1:
            frame_faces.remove(get_top_faces(frame_faces).pop()) # remove top face from frame_faces
        arch_face, arch_frame_faces = create_arch(bm, top_edges, frame_faces, prop.arch, prop.frame_thickness, local_xyz(face))
        frame_faces += arch_frame_faces

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    # add depths
    if frame_faces:
        frame_front_faces, frame_side_faces = add_frame_depth(bm, frame_faces, prop.frame_depth, normal)
        frame_faces = frame_front_faces + frame_side_faces

    if prop.add_arch:
        arch_face, new_frame_faces = add_arch_depth(bm, arch_face, prop.arch.depth, normal)
        frame_faces += new_frame_faces

    door_faces, new_frame_faces = add_multi_door_depth(bm, door_faces, prop.dw_depth, normal)
    frame_faces += new_frame_faces
    window_faces, new_frame_faces = add_multi_window_depth(bm, window_faces, prop.dw_depth, normal)
    frame_faces += new_frame_faces

    # add face maps
    add_faces_to_map(bm, door_faces, FaceMap.DOOR)
    add_faces_to_map(bm, window_faces, FaceMap.WINDOW)
    add_faces_to_map(bm, frame_faces, FaceMap.FRAME)
    if prop.add_arch:
        add_faces_to_map(bm, [arch_face], FaceMap.DOOR)

    return door_faces, window_faces, arch_face


def add_multi_door_depth(bm, door_faces, depth, normal):
    new_door_faces = []
    new_frame_faces = []
    for door in door_faces:
        df, ff = add_door_depth(bm, door, depth, normal)
        new_door_faces.append(df)
        new_frame_faces += ff
    return new_door_faces, new_frame_faces


def add_multi_window_depth(bm, window_faces, depth, normal):
    new_window_faces = []
    new_frame_faces = []
    for window in window_faces:
        wf, ff = add_door_depth(bm, window, depth, normal)
        new_window_faces.append(wf)
        new_frame_faces += ff
    return new_window_faces, new_frame_faces


def make_multigroup_insets(bm, face, size, frame_thickness, dws):
    if frame_thickness > 0:
        dw_count = count(dws)
        dw_width = (size.x - frame_thickness * (dw_count + 1)) / dw_count
        door_height = calc_face_dimensions(face)[1] - frame_thickness
        window_height = size.y - 2 * frame_thickness

        # adjacent doors/windows clubbed
        clubbed_widths = [clubbed_width(dw_width, frame_thickness, dw['type'], dw['count'], i==0, i==len(dws)-1) for i,dw in enumerate(dws)]
        clubbed_faces = subdivide_face_horizontally(bm, face, clubbed_widths)

        doors = []
        windows = []
        frames = []

        for i,(dw,f) in enumerate(zip(dws, clubbed_faces)):
            if dw['type'] == 'door':
                ds, fs = make_door_insets(bm, f, dw['count'], door_height, dw_width, frame_thickness, i==0, i==len(dws)-1)
                doors.extend(ds)
                frames.extend(fs)
            elif dw['type'] == 'window':
                ws, fs = make_window_insets(bm, f, dw['count'], window_height, dw_width, frame_thickness, i==0, i==len(dws)-1)
                windows.extend(ws)
                frames.extend(fs)
        return doors, windows, frames
    else:
        dw_count = count(components)
        dw_width = size.x / dw_count
        widths = [dw_width] * dw_count
        return subdivide_face_horizontally(bm, face, widths), [], []


def clubbed_width(width, frame_thickness, type, count, first=False, last=False):
    if type == "door":
        return (width * count) + (frame_thickness * (count+1))
    elif type == "window":
        if first and last:
            return (width * count) + (frame_thickness * (count+1))
        elif first or last:
            return (width * count) + (frame_thickness * count)
        else:
            return (width * count) + (frame_thickness * (count-1))


def make_window_insets(bm, face, count, window_height, window_width, frame_thickness, first=False, last=False):
    # split vertically for window
    face_height = calc_face_dimensions(face)[1]
    res = subdivide_face_vertically(bm, face, [face_height - (window_height+2*frame_thickness), window_height+2*frame_thickness])
    if not res:
        return [], []

    face = res[1]
    # vertical frame
    if first and last:
        h_widths = [frame_thickness, window_width] * count + [frame_thickness]
    elif first:
        h_widths = [frame_thickness, window_width] * count
    elif last:
        h_widths = [window_width, frame_thickness] * count
    else:
        h_widths = [window_width, frame_thickness] * (count-1) + [window_width]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # horizontal frames
    if first:
        work_faces = h_faces[1::2]
        v_frames = h_faces[::2]
    else:
        work_faces = h_faces[::2]
        v_frames = h_faces[1::2]
    v_widths = [frame_thickness, window_height, frame_thickness]
    v_faces = [f for h_face in work_faces for f in subdivide_face_vertically(bm, h_face, v_widths)]

    return v_faces[1::3], v_frames + v_faces[::3] + v_faces[2::3]


def make_door_insets(bm, face, count, door_height, door_width, frame_thickness, first=False, last=False):
    # vertical frame
    h_widths = [frame_thickness, door_width] * count + [frame_thickness]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # horizontal frames
    v_widths = [door_height, frame_thickness]
    v_faces = [f for h_face in h_faces[1::2] for f in subdivide_face_vertically(bm, h_face, v_widths)]
    return v_faces[::2], h_faces[::2] + v_faces[1::2]


def count(dws):
    return sum(dw["count"] for dw in dws)


def parse_components(components):
    char_to_type = {
        "d": "door",
        "w": "window",
    }
    previous = None
    dws = []
    for c in components:
        if c == previous:
            dws[-1]["count"] += 1
        else:
            dws.append({"type": char_to_type.get(c), "count": 1})
            previous = c
    return dws

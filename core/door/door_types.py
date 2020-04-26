import bmesh
from ..fill import fill_panel, fill_glass_panes, fill_louver, FillUser
from ..frame import (
    add_frame_depth,
)
from ..arch import (
    fill_arch,
    create_arch,
    add_arch_depth,
)
from ...utils import (
    valid_ngon,
    FaceMap,
    filter_geom,
    popup_message,
    map_new_faces,
    add_faces_to_map,
    calc_face_dimensions,
    add_facemap_for_groups,
    subdivide_face_horizontally,
    subdivide_face_vertically,
    get_top_edges,
    get_top_faces,
    get_bottom_faces,
    local_xyz,
    extrude_face_region,
)


def create_door(bm, faces, prop):
    """Create door from face selection
    """
    for face in faces:
        if not valid_ngon(face):
            popup_message("Door creation not supported non-rectangular n-gon!", "Ngon Error")
            return False

        face.select = False

        array_faces = subdivide_face_horizontally(bm, face, widths=[prop.size_offset.size.x]*prop.count)
        for aface in array_faces:
            face = create_door_split(bm, aface, prop.size_offset.size, prop.size_offset.offset)
            door, arch = create_door_frame(bm, face, prop)
            create_door_fill(bm, door, prop)
            if prop.add_arch:
                fill_arch(bm, arch, prop)
    return True


@map_new_faces(FaceMap.WALLS)
def create_door_split(bm, face, size, offset):
    """Use properties from SizeOffset to subdivide face into regular quads
    """

    wall_w, wall_h = calc_face_dimensions(face)
    # horizontal split
    h_widths = [wall_w/2 + offset.x - size.x/2, size.x, wall_w/2 - offset.x - size.x/2]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical split
    v_width = [wall_h/2 + offset.y + size.y/2, wall_h/2 - offset.y - size.y/2]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_width)

    return v_faces[0]


def create_door_frame(bm, face, prop):
    """Extrude and inset face to make door frame
    """
    normal = face.normal.copy()

    door_face, frame_faces = make_door_inset(bm, face, prop.size_offset.size, prop.frame_thickness)
    arch_face = None

    # create arch
    if prop.add_arch:
        frame_faces.remove(get_top_faces(frame_faces).pop()) # remove top face from frame_faces
        top_edges = get_top_edges({e for f in get_bottom_faces(frame_faces, n=2) for e in f.edges}, n=2)
        arch_face, arch_frame_faces = create_arch(bm, top_edges, frame_faces, prop.arch, prop.frame_thickness, local_xyz(face))
        frame_faces += arch_frame_faces

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    # add depths
    if prop.add_arch:
        [door_face], _, [arch_face], frame_faces = add_frame_depth(bm, [door_face], [], [arch_face], frame_faces, prop.frame_depth, normal)
        arch_face, new_frame_faces = add_arch_depth(bm, arch_face, prop.arch.depth, normal)
        frame_faces += new_frame_faces
    else:
        [door_face], _, _, frame_faces = add_frame_depth(bm, [door_face], [], [], frame_faces, prop.frame_depth, normal)

    door_face, new_frame_faces = add_door_depth(bm, door_face, prop.door_depth, normal)
    frame_faces += new_frame_faces

    # add face maps
    add_faces_to_map(bm, [door_face], FaceMap.DOOR)
    add_faces_to_map(bm, frame_faces, FaceMap.FRAME)
    if prop.add_arch:
        add_faces_to_map(bm, [arch_face], FaceMap.DOOR)

    return door_face, arch_face


def add_door_depth(bm, door, depth, normal):
    if depth > 0.0:
        door_faces, frame_faces = extrude_face_region(bm, [door], -depth, normal)
        return door_faces[0], frame_faces
    else:
        return door, []


def create_door_fill(bm, face, prop):
    """Add decorative elements on door face
    """
    if prop.double_door:
        faces = subdivide_face_horizontally(bm, face, widths=[1, 1])
        for f in faces:
            fill_door_face(bm, f, prop)
    else:
        fill_door_face(bm, face, prop)


def fill_door_face(bm, face, prop):
    """ Fill individual door face
    """
    if prop.fill_type == "PANELS":
        add_facemap_for_groups(FaceMap.DOOR_PANELS)
        fill_panel(bm, face, prop.panel_fill)
    elif prop.fill_type == "GLASS_PANES":
        add_facemap_for_groups(FaceMap.DOOR_PANES)
        fill_glass_panes(bm, face, prop.glass_fill, user=FillUser.DOOR)
    elif prop.fill_type == "LOUVER":
        add_facemap_for_groups(FaceMap.DOOR_LOUVERS)
        fill_louver(bm, face, prop.louver_fill, user=FillUser.DOOR)


def make_door_inset(bm, face, size, frame_thickness):
    """ Make one horizontal cut and two vertical cuts on face
    """
    door_width = size.x - frame_thickness * 2
    _, face_height = calc_face_dimensions(face)
    door_height = face_height - frame_thickness
    # horizontal cuts
    h_widths = [frame_thickness, door_width, frame_thickness]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical cuts
    v_widths = [door_height, frame_thickness]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_widths)
    return v_faces[0], h_faces[::2] + [v_faces[1]]

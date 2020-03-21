import bmesh
from bmesh.types import BMEdge
from ..fill import fill_panel, fill_glass_panes, fill_louver, FillUser
from ..common.frame import (
    add_frame_depth,
)
from ..common.arch import (
    fill_arch,
    create_arch,
    add_arch_depth,
)
from ...utils import (
    is_ngon,
    FaceMap,
    filter_geom,
    popup_message,
    map_new_faces,
    add_faces_to_map,
    calc_face_dimensions,
    add_facemap_for_groups,
    subdivide_face_edges_vertical,
    subdivide_face_horizontally,
    subdivide_face_vertically,
    get_top_edges,
    get_top_faces,
    get_bottom_faces,
    local_xyz,
)


def create_door(bm, faces, prop):
    """Create door from face selection
    """
    for face in faces:
        if is_ngon(face):
            popup_message("Door creation not supported for n-gons!", "Ngon Error")
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


@map_new_faces(FaceMap.DOOR_FRAMES, skip=FaceMap.DOOR)
def create_door_frame(bm, face, prop):
    """Extrude and inset face to make door frame
    """
    normal = face.normal.copy()

    door_face, frame_faces = make_door_inset(bm, face, prop.size_offset.size, prop.frame_thickness)
    arch_face = None

    if prop.add_arch:
        frame_faces.remove(get_top_faces(frame_faces).pop()) # remove top face from frame_faces
        top_edges = get_top_edges({e for f in get_bottom_faces(frame_faces, n=2) for e in f.edges}, n=2)
        arch_face, arch_frame_faces = create_arch(bm, top_edges, frame_faces, prop.arch, prop.frame_thickness, local_xyz(face))
        frame_faces += arch_frame_faces
        arch_face = add_arch_depth(bm, arch_face, prop.arch.depth, normal)

    door_face = add_door_depth(bm, door_face, prop.door_depth, normal)

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if frame_faces:
        add_frame_depth(bm, frame_faces, prop.frame_depth, normal)

    add_faces_to_map(bm, [door_face], FaceMap.DOOR)
    return door_face, arch_face


def add_door_depth(bm, door, depth, normal):
    if depth > 0.0:
        door = bmesh.ops.extrude_discrete_faces(bm, faces=[door]).get("faces").pop()
        bmesh.ops.translate(bm, verts=door.verts, vec=-normal * depth)
        return door
    else:
        return door



def create_door_fill(bm, face, prop):
    """Add decorative elements on door face
    """
    if prop.double_door:
        res = subdivide_face_edges_vertical(bm, face, 1)
        inner_edges = filter_geom(res["geom_inner"], bmesh.types.BMEdge)
        faces = list({f for e in inner_edges for f in e.link_faces})
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
    if frame_thickness > 0:
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
    else:
        return face, []


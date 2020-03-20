import bmesh
from ..common.frame import (
    add_frame_depth,
)
from ..common.arch import (
    fill_arch,
    create_arch,
    add_arch_depth,
)
from ..door.door_types import (
    add_door_depth,
    create_door_fill,
)
from ...utils import (
    is_ngon,
    FaceMap,
    popup_message,
    map_new_faces,
    add_faces_to_map,
    calc_face_dimensions,
    get_top_faces,
    get_bottom_faces,
    get_top_edges,
    subdivide_face_horizontally,
    subdivide_face_vertically,
    local_xyz,
)


def create_multidoor(bm, faces, prop):
    """ Create multidoor from face selection
    """

    for face in faces:
        if is_ngon(face):
            popup_message("Multidoor creation not supported for n-gons!", "Ngon Error")
            return False
    
        face.select = False

        array_faces = subdivide_face_horizontally(bm, face, widths=[prop.size_offset.size.x]*prop.array.count)
        for aface in array_faces:
            face = create_multidoor_split(bm, aface, prop.size_offset.size, prop.size_offset.offset)
            doors, arch = create_multidoor_frame(bm, face, prop)
            for door in doors:
                create_door_fill(bm, door, prop)
            fill_arch(bm, arch, prop)
    return True


@map_new_faces(FaceMap.WALLS)
def create_multidoor_split(bm, face, size, offset):
    """ Use properties from SizeOffset to subdivide face into regular quads
    """

    wall_w, wall_h = calc_face_dimensions(face)
    # horizontal split
    h_widths = [wall_w/2 + offset.x - size.x/2, size.x, wall_w/2 - offset.x - size.x/2]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical split
    v_width = [wall_h/2 - offset.y + size.y/2, wall_h/2 + offset.y - size.y/2]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_width)

    return v_faces[0]


@map_new_faces(FaceMap.DOOR_FRAMES, skip=FaceMap.DOOR)
def create_multidoor_frame(bm, face, prop):
    """ Extrude and inset face to make multidoor frame
    """
    normal = face.normal.copy()

    door_faces, frame_faces = make_multidoor_insets(bm, face, prop.size_offset.size, prop.frame_thickness, prop.door_count)
    arch_face = None

    if prop.has_arch():
        if prop.door_count == 1:
            frame_faces.remove(get_top_faces(frame_faces).pop()) # remove top face from frame_faces
        top_edges = get_top_edges({e for f in get_bottom_faces(frame_faces, n=prop.door_count+1) for e in f.edges}, n=prop.door_count+1)
        arch_face, arch_frame_faces = create_arch(bm, top_edges, frame_faces, prop.arch, prop.frame_thickness, local_xyz(face))
        frame_faces += arch_frame_faces
        arch_face = add_arch_depth(bm, arch_face, prop.arch.offset, normal)

    door_faces = [add_door_depth(bm, door, prop.door_depth, normal) for door in door_faces]

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if frame_faces:
        add_frame_depth(bm, frame_faces, prop.frame_depth, normal)

    add_faces_to_map(bm, door_faces, FaceMap.DOOR)
    return door_faces, arch_face


def make_multidoor_insets(bm, face, size, frame_thickness, door_count):
    if frame_thickness > 0:
        door_width = (size.x - frame_thickness * (door_count + 1)) / door_count
        _, face_height = calc_face_dimensions(face)
        door_height = face_height - frame_thickness
        # vertical frame
        h_widths = [frame_thickness, door_width] * door_count + [frame_thickness]
        h_faces = subdivide_face_horizontally(bm, face, h_widths)
        # horizontal frame
        v_widths = [door_height, frame_thickness]
        v_faces = [f for h_face in h_faces[1::2] for f in subdivide_face_vertically(bm, h_face, v_widths)]
        return v_faces[::2], h_faces[::2] + v_faces[1::2]
    else:
        door_width = size.x / door_count
        widths = [door_width] * door_count
        return subdivide_face_horizontally(bm, face, widths), []

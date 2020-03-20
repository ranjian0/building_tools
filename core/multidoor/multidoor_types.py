import bmesh
from bmesh.types import BMEdge

from ..fill import fill_panel, fill_glass_panes, fill_louver, FillUser
from ...utils import (
    is_ngon,
    FaceMap,
    arc_edge,
    filter_geom,
    popup_message,
    map_new_faces,
    add_faces_to_map,
    calc_face_dimensions,
    subdivide_face_edges_vertical,
    get_bottom_faces,
    get_top_edges,
    sort_verts,
    subdivide_face_horizontally,
    subdivide_face_vertically,
    local_xyz,
    add_facemap_for_groups,
)

from mathutils import Vector


def create_multidoor(bm, faces, prop):
    """Create multidoor from face selection
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
    """Use properties from SplitOffset to subdivide face into regular quads
    """

    wall_w, wall_h = calc_face_dimensions(face)
    # horizontal split
    h_widths = [wall_w/2 + offset.x - size.x/2, size.x, wall_w/2 - offset.x - size.x/2]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical split
    v_width = [wall_h/2 - offset.y + size.y/2, wall_h/2 + offset.y - size.y/2]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_width)

    return v_faces[0]


def create_multidoor_array(bm, face, prop):
    """Use ArrayProperty to subdivide face horizontally/vertically for further processing
    """
    if prop.door_count <= 1:
        return [face]
    return subdivide_face_horizontally(bm, face, prop.door_count*[prop.size_offset.size.x/prop.door_count])


@map_new_faces(FaceMap.DOOR_FRAMES, skip=FaceMap.DOOR)
def create_multidoor_frame(bm, face, prop):
    """Extrude and inset face to make multidoor frame
    """
    normal = face.normal.copy()

    door_faces, frame_faces = make_multidoor_insets(bm, face, prop.size_offset.size, prop.frame_thickness, prop.door_count)
    arch_face = None

    if prop.has_arch():
        top_edges = get_top_edges({e for f in get_bottom_faces(frame_faces, n=2) for e in f.edges}, n=2)
        arch_face, arch_frame_faces = arc_frame_edges(bm, face, top_edges, frame_faces, prop.arch, prop.frame_thickness)
        frame_faces += arch_frame_faces
        if prop.arch.offset != 0:
            arch_face = bmesh.ops.extrude_discrete_faces(bm, faces=[arch_face]).get("faces").pop()
            verts = [v for v in arch_face.verts]
            bmesh.ops.translate(bm, verts=verts, vec=-normal * prop.arch.offset)

    if prop.door_depth > 0.0:
        door_faces = bmesh.ops.extrude_discrete_faces(bm, faces=door_faces).get("faces")
        verts = [v for f in door_faces for v in f.verts]
        bmesh.ops.translate(bm, verts=verts, vec=-normal * prop.door_depth)

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if frame_faces and prop.frame_depth > 0.0:
        geom = bmesh.ops.extrude_face_region(bm, geom=frame_faces).get("geom")
        verts = filter_geom(geom, bmesh.types.BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=normal * prop.frame_depth)

    add_faces_to_map(bm, door_faces, FaceMap.DOOR)
    return door_faces, arch_face


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


def fill_arch(bm, face, prop):
    """ Fill arch
    """
    if prop.fill_type == "GLASS_PANES":
        add_facemap_for_groups(FaceMap.DOOR_PANES)
        pane_arch_face(bm, face, prop.glass_fill)


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


def arc_frame_edges(bm, face, top_edges, frame_faces, arch_prop, frame_thickness):
    verts = sort_verts([v for e in top_edges for v in e.verts], local_xyz(face)[1])
    arc_edges = [
        bmesh.ops.connect_verts(bm, verts=[verts[0],verts[3]])['edges'].pop(),
        bmesh.ops.connect_verts(bm, verts=[verts[1],verts[2]])['edges'].pop(),
    ]

    upper_arc = filter_geom(arc_edge(bm, arc_edges[0], arch_prop.resolution, arch_prop.height, arch_prop.offset, arch_prop.function)["geom_split"], BMEdge)
    lower_arc = filter_geom(arc_edge(bm, arc_edges[1], arch_prop.resolution, arch_prop.height-frame_thickness, arch_prop.offset, arch_prop.function)["geom_split"], BMEdge)
    arc_edges = [
        *upper_arc,
        *lower_arc,
    ]

    arch_frame_faces = bmesh.ops.bridge_loops(bm, edges=arc_edges)["faces"]
    arch_face = min(lower_arc[arch_prop.resolution//2].link_faces, key=lambda f: f.calc_center_median().z)
    return arch_face, arch_frame_faces


@map_new_faces(FaceMap.DOOR_PANES)
def pane_arch_face(bm, face, prop):
    bmesh.ops.inset_individual(
        bm, faces=[face], thickness=prop.pane_margin * 0.75, use_even_offset=True
    )
    bmesh.ops.translate(
        bm, verts=face.verts, vec=-face.normal * prop.pane_depth
    )

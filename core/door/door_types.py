import bmesh
from mathutils import Vector
from bmesh.types import BMEdge

from ..fill import fill_panel, fill_glass_panes, fill_louver, FillUser
from ...utils import (
    FaceMap,
    validate,
    arc_edge,
    filter_geom,
    map_new_faces,
    local_to_global,
    face_with_verts,
    add_faces_to_map,
    calc_edge_median,
    calc_face_dimensions,
    filter_vertical_edges,
    add_facemap_for_groups,
    inset_face_with_scale_offset,
    subdivide_face_edges_vertical,
)


def create_door(bm, faces, prop):
    """Create door from face selection
    """
    for face in faces:
        array_faces = create_door_array(bm, face, prop.array)

        for aface in array_faces:
            face = create_door_split(bm, aface, prop.size_offset)
            if not face:
                continue

            face = create_door_frame(bm, face, prop)
            create_door_fill(bm, face, prop)


@map_new_faces(FaceMap.WALLS)
def create_door_split(bm, face, prop):
    """Use properties from SplitOffset to subdivide face into regular quads
    """
    wall_w, wall_h = calc_face_dimensions(face)
    scale_x = prop.size.x / wall_w
    scale_y = prop.size.y / wall_h
    offset = local_to_global(face, Vector((prop.offset.x, prop.offset.y, 0.0)))
    return inset_face_with_scale_offset(bm, face, scale_y, scale_x, offset.x, offset.y)


def create_door_array(bm, face, prop):
    """Use ArrayProperty to subdivide face horizontally/vertically for further processing
    """
    if prop.count <= 1:
        return [face]
    res = subdivide_face_edges_vertical(bm, face, prop.count - 1)
    inner_edges = filter_geom(res["geom_inner"], bmesh.types.BMEdge)
    return list({f for e in inner_edges for f in e.link_faces})


@map_new_faces(FaceMap.DOOR_FRAMES, skip=FaceMap.DOOR)
def create_door_frame(bm, face, prop):
    """Extrude and inset face to make door frame
    """
    # -- dissolve bottom edge
    edges = sorted(face.edges, key=lambda ed: calc_edge_median(ed).z)
    bmesh.ops.dissolve_edges(bm, edges=edges[:1], use_verts=True)
    face = min(edges.pop().link_faces, key=lambda f: f.calc_center_median().z)

    if prop.has_arch():
        return create_door_frame_arched(bm, face, prop)

    frame_faces = []
    normal = face.normal.copy()
    if prop.frame_thickness > 0:
        face = make_door_inset(bm, face, prop)

        faces = [f for e in face.edges for f in e.link_faces]
        frame_faces = list(
            filter(lambda f: f is not face and f.normal == normal, faces)
        )

    if prop.door_depth > 0.0:
        face = bmesh.ops.extrude_discrete_faces(bm, faces=[face]).get("faces").pop()
        bmesh.ops.translate(bm, verts=face.verts, vec=-normal * prop.door_depth)

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if frame_faces and prop.frame_depth > 0.0:
        geom = bmesh.ops.extrude_face_region(bm, geom=frame_faces).get("geom")
        verts = filter_geom(geom, bmesh.types.BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=normal * prop.frame_depth)

    add_faces_to_map(bm, [face], FaceMap.DOOR)
    return face


def create_door_frame_arched(bm, face, prop):
    """ Arch the top edge of face and make door frame
    """
    arc_edges = []
    top = sorted(face.edges, key=lambda ed: calc_edge_median(ed).z).pop()
    arc_edges.append(top)

    frame_faces = []
    normal = face.normal.copy()
    if prop.frame_thickness > 0:
        face = make_door_inset(bm, face, prop)

        faces = [f for e in face.edges for f in e.link_faces]
        frame_faces = list(
            filter(lambda f: f is not face and f.normal == normal, faces)
        )

        top2 = sorted(face.edges, key=lambda ed: calc_edge_median(ed).z).pop()
        merge_corner_vertices(bm, top2)
        arc_edges.append(top2)

    frame_faces = arc_frame_edges(bm, arc_edges, frame_faces, prop.arch)

    verts = sorted(face.verts, key=lambda v: v.co.z)
    edge = bmesh.ops.connect_verts(bm, verts=verts[2:4]).get("edges").pop()

    faces = extrude_door_and_frame_depth(bm, edge.link_faces, frame_faces, normal, prop)
    if faces:
        add_faces_to_map(bm, faces, FaceMap.DOOR)
        return sorted(faces, key=lambda f: f.calc_center_median().z)[0]
    return min(edge.link_faces, key=lambda f: f.calc_center_median().z)


def create_door_fill(bm, face, prop):
    """Add decorative elements on door face
    """
    if prop.fill_type == "PANELS":
        add_facemap_for_groups(FaceMap.DOOR_PANELS)
        fill_panel(bm, face, prop.panel_fill)
    elif prop.fill_type == "GLASS_PANES":
        add_facemap_for_groups(FaceMap.DOOR_PANES)
        if prop.has_arch():
            pane_arch_face(bm, face, prop.glass_fill)
        fill_glass_panes(bm, face, prop.glass_fill, user=FillUser.DOOR)
    elif prop.fill_type == "LOUVER":
        add_facemap_for_groups(FaceMap.DOOR_LOUVERS)
        fill_louver(bm, face, prop.louver_fill, user=FillUser.DOOR)


def make_door_inset(bm, face, prop):
    """Make one horizontal cut and two vertical cuts on face
    """
    edges = filter_vertical_edges(face.edges, face.normal)
    top_edge = split_edges_horizontal_offset_top(bm, edges, prop.frame_thickness)
    face = min(top_edge.link_faces, key=lambda f: f.calc_center_median().z)

    w = calc_face_dimensions(face)[0]
    off = (w / 3) - prop.frame_thickness
    edges = split_face_vertical_with_offset(bm, face, 2, [off, off])
    face = (set(edges[0].link_faces) & set(edges[1].link_faces)).pop()
    return face


def merge_corner_vertices(bm, edge):
    """ Merge highest verts linked to edge with verts above them
    """
    verts = {vert for v in edge.verts for e in v.link_edges for vert in e.verts}
    verts = list(filter(lambda v: v not in edge.verts, verts))

    top_verts = sorted(verts, key=lambda v: v.co.z)[2:]
    for vert in top_verts:
        upper_verts = [v for e in vert.link_edges for v in e.verts]
        upper_link = sorted(upper_verts, key=lambda v: v.co.z).pop()
        bmesh.ops.pointmerge(bm, verts=[upper_link, vert], merge_co=upper_link.co)


def arc_frame_edges(bm, edges, frame_faces, prop):
    new_edges = []
    for e in edges:
        res = arc_edge(bm, e, prop.resolution, prop.height, prop.offset, prop.function)
        new_edges.extend(filter_geom(res["geom_split"], bmesh.types.BMEdge))

    res = bmesh.ops.bridge_loops(bm, edges=new_edges)
    bmesh.ops.delete(
        bm, geom=[f for f in frame_faces if len(f.verts) > 4], context="FACES"
    )
    return validate(set(frame_faces + res["faces"]))


def extrude_door_and_frame_depth(bm, door_faces, frame_faces, normal, prop):
    """ Create extrusions for door depth and frame depth
    """
    faces = None
    if prop.door_depth > 0.0:
        res = bmesh.ops.extrude_face_region(bm, geom=door_faces).get("geom")
        bmesh.ops.delete(bm, geom=door_faces, context="FACES")
        faces = filter_geom(res, bmesh.types.BMFace)
        verts = list({v for f in faces for v in f.verts})
        bmesh.ops.translate(bm, verts=verts, vec=-normal * prop.door_depth)

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if frame_faces and prop.frame_depth > 0.0:
        geom = bmesh.ops.extrude_face_region(bm, geom=frame_faces).get("geom")
        verts = filter_geom(geom, bmesh.types.BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=normal * prop.frame_depth)

    return faces


def split_face_vertical_with_offset(bm, face, cuts, offsets):
    """split a face(quad) vertically and move the new edges
    """
    median = face.calc_center_median()
    res = subdivide_face_edges_vertical(bm, face, cuts)
    edges = filter_geom(res["geom_inner"], BMEdge)
    edges.sort(
        key=lambda e: getattr(calc_edge_median(e), "x" if face.normal.y else "y")
    )

    for off, e in zip(offsets, edges):
        tvec = calc_edge_median(e) - median
        bmesh.ops.translate(bm, verts=e.verts, vec=tvec.normalized() * off)
    return edges


def split_edges_horizontal_offset_top(bm, edges, offset):
    """split a face(quad) horizontally and move the new edge
    """
    face = face_with_verts(bm, list({v for e in edges for v in e.verts}))
    v_edges = filter_vertical_edges(face.edges, face.normal)
    new_verts = []
    for e in v_edges:
        vert = max(list(e.verts), key=lambda v: v.co.z)
        v = bmesh.utils.edge_split(e, vert, offset / e.calc_length())[-1]
        new_verts.append(v)

    res = bmesh.ops.connect_verts(bm, verts=new_verts).get("edges")
    return res.pop()


@map_new_faces(FaceMap.DOOR_PANES)
def pane_arch_face(bm, face, prop):
    edge = sorted(face.edges, key=lambda ed: calc_edge_median(ed).z).pop()
    arch_face = sorted(edge.link_faces, key=lambda f: f.calc_center_median().z).pop()
    add_faces_to_map(bm, [arch_face], FaceMap.DOOR)
    bmesh.ops.inset_individual(
        bm, faces=[arch_face], thickness=prop.pane_margin * 0.75, use_even_offset=True
    )
    bmesh.ops.translate(
        bm, verts=arch_face.verts, vec=-arch_face.normal * prop.pane_depth
    )

import bmesh
from bmesh.types import BMEdge

from ..fill import fill_panel, fill_glass_panes, fill_louver
from ...utils import (
    arc_edge,
    filter_geom,
    face_with_verts,
    calc_edge_median,
    calc_face_dimensions,
    filter_vertical_edges,
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


def create_door_split(bm, face, prop):
    """Use properties from SplitOffset to subdivide face into regular quads
    """
    size, off = prop.size, prop.offset
    size_y = min(size.y, 0.9999)
    return inset_face_with_scale_offset(bm, face, size_y, size.x, off.x, off.y, off.z)


def create_door_array(bm, face, prop):
    """Use ArrayProperty to subdivide face horizontally/vertically for further processing
    """
    if prop.count <= 1:
        return [face]
    res = subdivide_face_edges_vertical(bm, face, prop.count - 1)
    inner_edges = filter_geom(res["geom_inner"], bmesh.types.BMEdge)
    return list({f for e in inner_edges for f in e.link_faces})


def create_door_frame(bm, face, prop):
    """Extrude and inset face to make door frame
    """
    # -- dissolve bottom edge
    bottom = sorted(face.edges, key=lambda ed: calc_edge_median(ed).z)
    bmesh.ops.dissolve_edges(bm, edges=bottom[:1], use_verts=True)
    face = [f for f in bm.faces if f.index == len(bm.faces) - 1].pop()

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

    arch = prop.arch
    for e in arc_edges:
        arc_edge(bm, e, arch.resolution, arch.height, arch.offset, arch.function)

    verts = sorted(face.verts, key=lambda v: v.co.z)
    edge = bmesh.ops.connect_verts(bm, verts=verts[2:4]).get("edges").pop()

    faces = extrude_door_and_frame_depth(bm, edge.link_faces, frame_faces, normal, prop)
    return sorted(faces, key=lambda f: f.calc_center_median().z)[0]


def create_door_fill(bm, face, prop):
    """Add decorative elements on door face
    """
    if prop.fill_type == "PANELS":
        fill_panel(bm, face, prop.panel_fill)
    elif prop.fill_type == "GLASS PANES":
        fill_glass_panes(bm, face, prop.glass_fill)
    elif prop.fill_type == "LOUVER":
        fill_louver(bm, face, prop.louver_fill)


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

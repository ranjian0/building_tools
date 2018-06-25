import bpy
import bmesh
from bmesh.types import BMEdge
from mathutils import Matrix, Vector
from ...utils import (
    split,
    split_quad,
    filter_geom,
    get_edit_mesh,
    face_with_verts,
    calc_edge_median,
    calc_face_dimensions,
    filter_vertical_edges,
    filter_horizontal_edges
    )

from ..fill import (
    fill_panel,
    fill_glass_panes,
    fill_louver,
    )

def make_door(bm, faces, **kwargs):
    """Create basic flush door

    Args:
        **kwargs: DoorProperty items
    """

    for face in faces:
        face = make_door_split(bm, face, **kwargs)
        # -- check that split was successful
        if not face:
            continue

        nfaces = make_door_double(bm, face, **kwargs)
        for face in nfaces:
            face = make_door_frame(bm, face, **kwargs)
            make_door_fill(bm, face, **kwargs)

def make_door_split(bm, face, size, off, **kwargs):
    """Use properties from SplitOffset to subdivide face into regular quads

    Args:
        bm   (bmesh.types.BMesh):  bmesh for current edit mesh
        face (bmesh.types.BMFace): face to make split (must be quad)
        size (vector2): proportion of the new face to old face
        off  (vector3): how much to offset new face from center
        **kwargs: Extra kwargs from DoorProperty

    Returns:
        bmesh.types.BMFace: New face created after split
    """
    return split(bm, face, size.y, size.x, off.x, off.y, off.z)

def make_door_frame(bm, face, ft, fd, **kwargs):
    """Create extrude and inset around a face to make door frame

    Args:
        bm   (bmesh.types.BMesh): bmesh of current edit mesh
        face (bmesh.types.BMFace): face to make frame for
        ft (float): Thickness of the door frame
        fd (float): Depth of the doorframe
        **kwargs: Extra kwargs from DoorProperty

    Returns:
        bmesh.types.BMFace: face after frame is created
    """
    def delete_hidden_face(_face):
        """ remove hidden bottom faces after frame extrusion """
        bottom_edge = min(filter_horizontal_edges(_face.edges, _face.normal),
                        key=lambda e : calc_edge_median(e).z)
        hidden = min([f for f in bottom_edge.link_faces],
                        key=lambda f : f.calc_center_median().z)
        bmesh.ops.delete(bm, geom=[hidden], context=5)

    # Frame outset
    face = bmesh.ops.extrude_discrete_faces(bm,
            faces=[face]).get('faces')[-1]
    bmesh.ops.translate(bm, verts=face.verts, vec=face.normal * fd)
    delete_hidden_face(face)

    # Make frame inset - frame thickness
    median = face.calc_center_median()
    if ft:
        # Vertical Splits
        w, _  = calc_face_dimensions(face)
        res   = split_quad(bm, face, True, 2)
        edges = filter_geom(res['geom_inner'], BMEdge)
        edges.sort(key=lambda e: getattr(calc_edge_median(e),
                    'x' if face.normal.y else 'y'))

        offsets = [(w/3), (w/3)]
        for off, e in zip(offsets, edges):
            tvec = calc_edge_median(e) - median
            bmesh.ops.translate(bm,
                verts=e.verts,
                vec=tvec.normalized() * (off-ft))

        # Top horizontal split
        face = face_with_verts(bm, list({v for e in edges for v in e.verts}))
        v_edges = filter_vertical_edges(face.edges, face.normal)
        new_verts = []
        for e in v_edges:
            vert = max(list(e.verts), key=lambda v: v.co.z)
            _, v = bmesh.utils.edge_split(e, vert, ft / e.calc_length())
            new_verts.append(v)

        res = bmesh.ops.connect_verts(bm, verts=new_verts).get('edges')
        face = min(list({f for e in res for f in e.link_faces}),
                key=lambda f: f.calc_center_median().z)

    # # Make frame extrude - frame depth
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if fd:
        f = bmesh.ops.extrude_discrete_faces(bm,
                faces=[face]).get('faces')[-1]
        bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * fd)
        delete_hidden_face(f)
        return f
    return face

def make_door_double(bm, face, hdd, **kwargs):
    """Split face vertically into two faces

    Args:
        bm   (bmesh.types.BMesh): bmesh for current edit mesh
        face (bmesh.types.BMFace): face to operate on
        hdd  (bool): whether to make the double door
        **kwargs: Extra kwargs from DoorPoperty

    Returns:
        list: face(s) after double door created
    """
    if hdd:
        ret = bmesh.ops.subdivide_edges(bm,
            edges=filter_horizontal_edges(face.edges, face.normal),
            cuts=1).get('geom_inner')

        return list(filter_geom(ret, BMEdge)[-1].link_faces)
    return [face]

def make_door_fill(bm, face, fill_type, **kwargs):
    """Create extra elements on face

    Args:
        bm   (bmesh.types.BMesh): bmesh for current edit mesh
        face (bmesh.types.BMFace): face to operate on
        fill_type (str): Type of elements to add
        **kwargs: Extra kwargs from DoorProperty
    """
    if fill_type == 'NONE':
        pass

    elif fill_type == 'PANELS':
        fill_panel(bm, face, **kwargs)

    elif fill_type == 'GLASS PANES':
        fill_glass_panes(bm, face, **kwargs)

    elif fill_type == 'LOUVER':
        fill_louver(bm, face, **kwargs)

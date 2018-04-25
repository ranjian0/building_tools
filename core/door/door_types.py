import bpy
import bmesh
from bmesh.types import BMEdge
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

from ..util_fill import (
    fill_panel,
    fill_glass_panes,
    fill_louver,
    )

def make_door(**kwargs):
    """Create basic flush door

    Args:
        **kwargs: DoorProperty items
    """

    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    faces = (f for f in bm.faces if f.select)
    for face in faces:
        face = make_door_split(bm, face, **kwargs)

        nfaces = make_door_double(bm, face, **kwargs)
        for face in nfaces:
            face = make_door_frame(bm, face, **kwargs)
            make_door_fill(bm, face, **kwargs)

    bmesh.update_edit_mesh(me, True)

def make_door_split(bm, face, size, off, **kwargs):
    return split(bm, face, size.y, size.x, off.x, off.y, off.z)

def make_door_frame(bm, face, ft, fd, **kwargs):

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
    if ft:
        # Vertical Splits
        w, _ = calc_face_dimensions(face)
        res  = split_quad(bm, face, True, 2)
        edges = filter_geom(res['geom_inner'], BMEdge)
        edges.sort(key=lambda e: getattr(calc_edge_median(e),
                    'x' if face.normal.y else 'y'))

        offsets = [(-w/3) + ft, (w/3) - ft]
        for off, e in zip(offsets, edges):
            bmesh.ops.translate(bm,
                verts=e.verts,
                vec=(off, 0, 0) if face.normal.y else (0, off, 0))

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

    # Make frame extrude - frame depth
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if fd:
        f = bmesh.ops.extrude_discrete_faces(bm,
            faces=[face]).get('faces')[-1]
        bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * fd)
        delete_hidden_face(f)
        return f
    return face

def make_door_double(bm, face, hdd, **kwargs):
    if hdd:
        ret = bmesh.ops.subdivide_edges(bm,
            edges   = filter_horizontal_edges(face.edges, face.normal),
            cuts    =1).get('geom_inner')

        return list(filter_geom(ret, BMEdge)[-1].link_faces)
    return [face]

def make_door_fill(bm, face, fill_type, **kwargs):

    if fill_type == 'NONE':
        pass

    elif fill_type == 'PANELS':
        fill_panel(bm, face, **kwargs)

    elif fill_type == 'GLASS PANES':
        fill_glass_panes(bm, face, **kwargs)

    elif fill_type == 'LOUVER':
        fill_louver(bm, face, **kwargs)
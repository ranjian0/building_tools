import bpy
import bmesh
from bmesh.types import BMEdge, BMVert
from mathutils import Vector
from ...utils import (
        split,
        filter_geom,
        get_edit_mesh,
        filter_vertical_edges,
        filter_horizontal_edges
    )

from ..util_fill import (
    fill_panel,
    fill_glass_panes,
    fill_louver,
)

def door_basic(cls, **kwargs):
    """Create basic flush door

    Args:
        cls: parent door class
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
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts))

    # Make frame inset - frame thickness
    if ft:
        bmesh.ops.inset_individual(bm, faces=[face], thickness=ft)

    # Make frame extrude - frame depth
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if fd:
        f = bmesh.ops.extrude_discrete_faces(bm,
            faces=[face]).get('faces')[-1]
        bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * fd)

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
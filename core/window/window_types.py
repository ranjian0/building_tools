import bpy
import bmesh
from ...utils import (
    split,
    get_edit_mesh,
    )

from ..util_fill import (
    fill_bar,
    fill_louver,
    fill_glass_panes
    )


def make_window(cls, **kwargs):
    """Generate a basic window

    Args:
        cls: parent window class
        **kwargs: WindowProperty items
    """

    # Get active mesh
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    faces = [f for f in bm.faces if f.select]
    for face in faces:
        face = make_window_split(bm, face, **kwargs)
        # -- check that split was successful
        if not face:
            return
        face = make_window_frame(bm, face, **kwargs)
        make_window_fill(bm, face, **kwargs)

    bmesh.update_edit_mesh(me, True)

def make_window_split(bm, face, size, off, **kwargs):
    """ Basically scales down the face given based on parameters """
    return split(bm, face, size.y, size.x, off.x, off.y, off.z)

def make_window_frame(bm, face, ft, fd, **kwargs):
    """ Inset and extrude to create a frame """
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts))
    face = bmesh.ops.extrude_discrete_faces(bm,
        faces=[face]).get('faces')[-1]
    bmesh.ops.translate(bm, verts=face.verts, vec=face.normal * fd/2)

    if ft:
        bmesh.ops.inset_individual(bm, faces=[face], thickness=ft)

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if fd:
        f = bmesh.ops.extrude_discrete_faces(bm,
            faces=[face]).get('faces')[-1]
        bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * fd)

        return f
    return face

def make_window_fill(bm, face, fill_type, **kwargs):

    if fill_type == 'NONE':
        pass

    elif fill_type == 'GLASS PANES':
        fill_glass_panes(bm, face, **kwargs)

    elif fill_type == 'BAR':
        fill_bar(bm, face, **kwargs)

    elif fill_type == 'LOUVER':
        fill_louver(bm, face, **kwargs)

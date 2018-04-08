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

def door_basic(cls, **kwargs):
    """Create basic flush door

    Args:
        cls: parent door class
        **kwargs: DoorProperty items
    """
    # Get active mesh
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    faces = [f for f in bm.faces if f.select]

    for face in faces:

        # -- add a split
        face = make_door_split(bm, face, **kwargs)

        if not face:
            return

        # -- create door frame
        face = make_door_frame(bm, face, **kwargs)

        # -- chack double door
        nfaces = make_door_double(bm, face, **kwargs)


        for face in nfaces:
            # create door outline
            face = make_door_outline(bm, face, **kwargs)

            face = make_door_panes(bm, face, **kwargs)

            make_door_grooves(bm, face, **kwargs)

    bmesh.update_edit_mesh(me, True)

def make_door_split(bm, face, size, off, **kwargs):
    return split(bm, face, size.y, size.x, off.x, off.y, off.z)

def make_door_frame(bm, face, oft, ofd, **kwargs):

    # if there any double vertices we're in trouble
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts))

    # Make frame inset - frame thickness
    if oft > 0:
        res = bmesh.ops.inset_individual(bm, faces=[face], thickness=oft)

    # Make frame extrude - frame depth
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if ofd > 0:
        current_faces = list(bm.faces)
        ret = bmesh.ops.extrude_discrete_faces(bm, faces=[face])
        f = ret['faces'][0]
        bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * ofd)

        return f
    return face

def make_door_double(bm, face, hdd, **kwargs):
    if hdd:
        edgs = filter_horizontal_edges(face.edges, face.normal)
        ret = bmesh.ops.subdivide_edges(bm, edges=edgs, cuts=1)
        new_faces = list(filter_geom(ret['geom_inner'], BMEdge)[-1].link_faces)

        return new_faces
    return [face]

def make_door_outline(bm, face, ift, ifd, **kwargs):
    if ift > 0:
        res = bmesh.ops.inset_individual(bm, faces=[face], thickness=ift)

        if ifd > 0:
            current_faces = list(bm.faces)
            ret = bmesh.ops.extrude_discrete_faces(bm, faces=[face])
            f = ret['faces'][0]
            bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * ifd)
            return f
    return face

def make_door_panes(bm, face, panned, px, py, pt, pd, offset, width, **kwargs):
    if not panned:
        return face

    n = face.normal
    v_edges = filter_vertical_edges(face.edges, n)
    res = bmesh.ops.subdivide_edges(bm, edges=v_edges, cuts=2)
    edges = filter_geom(res['geom_inner'], BMEdge)

    ret_face = min({f for e in edges for f in e.link_faces}, key=lambda f: f.calc_center_median().z)

    bmesh.ops.scale(bm, verts=list({v for e in edges for v in e.verts}), vec=(1, 1, width))
    bmesh.ops.translate(bm, verts=list({v for e in edges for v in e.verts}), vec=(0, 0, offset))

    # get pane face
    pane_face = list(set(list(edges)[0].link_faces).intersection(set(list(edges)[1].link_faces)))[-1]
    bmesh.ops.inset_individual(bm, faces=[pane_face], thickness=0.01)

    # cut panes
    vedgs = filter_vertical_edges(pane_face.edges, n)
    hedgs = list((set(pane_face.edges).difference(vedgs)))

    res1 = bmesh.ops.subdivide_edges(bm, edges=vedgs, cuts=px)
    edgs = filter_geom(res1['geom_inner'], BMEdge)
    res2 = bmesh.ops.subdivide_edges(bm, edges=hedgs + edgs, cuts=py)

    # panels
    e = filter_geom(res2['geom_inner'], BMEdge)
    pane_faces = list({f for ed in e for f in ed.link_faces})
    panes = bmesh.ops.inset_individual(bm, faces=pane_faces, thickness=pt)

    for f in pane_faces:
        bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * pd)

    return ret_face

def make_door_grooves(bm, face, grov, gx, gy, gt, gd, gw, goff, **kwargs):
    if not grov:
        return

    # Create main groove to hold child grooves
    bmesh.ops.inset_individual(bm, faces=[face], thickness=gt)
    bmesh.ops.scale(bm, verts=list({v for e in face.edges for v in e.verts}), vec=(1, 1, gw))
    bmesh.ops.translate(bm, verts=list({v for e in face.edges for v in e.verts}), vec=(0, 0, goff))

    # Calculate edges to be subdivided
    n = face.normal
    vedgs = filter_vertical_edges(face.edges, n)
    hedgs = list((set(face.edges).difference(vedgs)))

    # Subdivide the edges
    res1 = bmesh.ops.subdivide_edges(bm, edges=vedgs, cuts=gx)
    edgs = filter_geom(res1['geom_inner'], BMEdge)
    res2 = bmesh.ops.subdivide_edges(bm, edges=hedgs + edgs, cuts=gy)

    # Get all groove faces
    vts = filter_geom(res2['geom_inner'], BMVert)
    faces = list(filter(lambda f: len(f.verts) == 4, {f for v in vts for f in v.link_faces if f.normal == n}))

    # Make groove
    bmesh.ops.inset_individual(bm, faces=faces, thickness=gt / 2)
    bmesh.ops.inset_individual(bm, faces=faces, thickness=gt / 2)

    v = list({v for f in faces for v in f.verts})
    bmesh.ops.translate(bm, verts=v, vec=n * gd)

    # Clean geometry
    vts2 = [v for e in filter_geom(res1['geom_split'], BMEdge) for v in e.verts]
    vts2.sort(key=lambda v: v.co.z)
    vts2 = vts2[2:len(vts2) - 2]

    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0)
    bmesh.ops.dissolve_verts(bm, verts=list(set(vts + vts2)))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

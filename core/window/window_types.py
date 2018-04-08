import bpy
import bmesh
from math import pi, sin
from pprint import pprint
from mathutils import Matrix, Vector
from bmesh.types import BMVert, BMEdge, BMFace
from ...utils import (
    split,
    filter_geom,
    square_face,
    get_edit_mesh,
    calc_edge_median,
    calc_face_dimensions,
    filter_vertical_edges,
    filter_horizontal_edges,
    )


def win_basic(cls, **kwargs):
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

        # -- add a split
        face = make_window_split(bm, face, **kwargs)

        # -- check that split was successful
        if not face:
            return

        # -- create window frame
        face = make_window_frame(bm, face, **kwargs)

        # -- add some window panes/bars
        fill = kwargs.get('fill')
        if fill == 'BAR':
            make_window_bars(bm, face, **kwargs)
        else:
            make_window_panes(bm, face, **kwargs)

    bmesh.update_edit_mesh(me, True)

def win_arched(cls, **kwargs):
    """Generate arched window

    Args:
        cls: parent window class
        **kwargs: WindowProperty items
    """

    # Get active mesh
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    faces = [f for f in bm.faces if f.select]

    for face in faces:
        # -- add a split
        face = make_window_split(bm, face, **kwargs)

        # -- check that split was successful
        if not face:
            return

        # subdivide the face horizontally
        e = filter_vertical_edges(face.edges, face.normal)
        res = bmesh.ops.subdivide_edges(bm, edges=e, cuts=1)
        nedge = filter_geom(res['geom_inner'], BMEdge)[-1]

        upper_face = face
        lower_face = list(set(nedge.link_faces).difference([upper_face]))[-1]

        # -- make upperface arch
        make_window_arch(bm, upper_face, **kwargs)

        # create window frame
        upper_face = make_window_frame(bm, upper_face, **kwargs)

        # Arch detail
        make_window_arch_detail(bm, upper_face, **kwargs)

        # -- make lowerface panes/bars
        lower_face = make_window_frame(bm, lower_face, **kwargs)

        fill = kwargs.get('fill')
        if fill == 'BAR':
            make_window_bars(bm, lower_face, **kwargs)
        else:
            make_window_panes(bm, lower_face, **kwargs)

    bmesh.update_edit_mesh(me, True)

def make_window_split(bm, face, size, off, **kwargs):
    """ Basically scales down the face given based on parameters """
    return split(bm, face, size.y, size.x, off.x, off.y, off.z)

def make_window_frame(bm, face, ft, fd, **kwargs):
    """ Inset and extrude to create a frame """

    # if there any double vertices we're in trouble
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts))

    # Make frame inset - frame thickness
    if ft > 0:
        res = bmesh.ops.inset_individual(bm, faces=[face], thickness=ft)


    # Make frame extrude - frame depth
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if fd > 0:
        current_faces = list(bm.faces)
        ret = bmesh.ops.extrude_discrete_faces(bm, faces=[face])
        f = ret['faces'][0]
        bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * fd)

        return f
    return face

def make_window_panes(bm, face, px, py, pt, pd, **kwargs):
    """ Create some window panes """

    n = face.normal
    v_edges = filter_vertical_edges(face.edges, n)
    h_edges = filter_horizontal_edges(face.edges, n)

    # -- if panes_x == 0, skip
    if px:
        res1 = bmesh.ops.subdivide_edges(bm, edges=v_edges, cuts=px)

    edgs = filter_geom(res1['geom_inner'], BMEdge) if px else []
    if py:
        res2 = bmesh.ops.subdivide_edges(bm, edges=h_edges + edgs, cuts=py)

    # panes
    # -- if we're here successfully, about 3 things may have happened
    do_panes = True
    if py:
        e = filter_geom(res2['geom_inner'], BMEdge)
    else:
        if px:
            e = edgs
        else:
            do_panes = False
    if do_panes:
        pane_faces = list({f for ed in e for f in ed.link_faces})
        panes = bmesh.ops.inset_individual(bm, faces=pane_faces, thickness=pt)

        for f in pane_faces:
            bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * pd)

    pass

def make_window_bars(bm, face, fd, px, py, pt, pd, **kwargs):
    """ Create window bars """

    # Calculate center, width and height of face
    width, height = calc_face_dimensions(face)
    fc = face.calc_center_median()

    # Create Inner Frames
    # -- horizontal
    offset = height / (px + 1)
    for i in range(px):
        # Duplicate
        ret = bmesh.ops.duplicate(bm, geom=[face])
        square_face(bm, filter_geom(ret['geom'], BMFace)[-1])
        verts = filter_geom(ret['geom'], BMVert)

        # Scale and translate
        bmesh.ops.scale(bm, verts=verts, vec=(1, 1, pt), space=Matrix.Translation(-fc))
        bmesh.ops.translate(bm, verts=verts,
                            vec=Vector((face.normal * fd / 2)) + Vector((0, 0, -height / 2 + (i + 1) * offset)))

        # Extrude
        ext = bmesh.ops.extrude_edge_only(bm,
                                          edges=filter_horizontal_edges(filter_geom(ret['geom'], BMEdge), face.normal))
        bmesh.ops.translate(bm, verts=filter_geom(ext['geom'], BMVert), vec=-face.normal * fd / 2)

    # -- vertical
    eps = 0.015
    offset = width / (py + 1)
    for i in range(py):
        # Duplicate
        ret = bmesh.ops.duplicate(bm, geom=[face])
        verts = filter_geom(ret['geom'], BMVert)

        # Scale and Translate
        bmesh.ops.scale(bm, verts=verts, vec=(pt, pt, 1), space=Matrix.Translation(-fc))
        perp = face.normal.cross(Vector((0, 0, 1)))
        bmesh.ops.translate(bm, verts=verts,
                            vec=Vector((face.normal * ((fd / 2) - eps))) + perp * (-width / 2 + ((i + 1) * offset)))

        # Extrude
        ext_edges = []

        # filter vertical edges
        # -- This part is redundant for good reasons, JUST DON'T!!

        if face.normal.x and face.normal.y:
            for e in filter_geom(ret['geom'], BMEdge):
                s = set([round(v.co.x, 4) for v in e.verts])
                if len(s) == 1:
                    ext_edges.append(e)
        elif face.normal.x and not face.normal.y:
            for e in filter_geom(ret['geom'], BMEdge):
                s = set([round(v.co.y, 4) for v in e.verts])
                if len(s) == 1:
                    ext_edges.append(e)
        elif face.normal.y and not face.normal.x:
            for e in filter_geom(ret['geom'], BMEdge):
                s = set([round(v.co.x, 4) for v in e.verts])
                if len(s) == 1:
                    ext_edges.append(e)
        else:
            raise NotImplementedError

        ext = bmesh.ops.extrude_edge_only(bm, edges=ext_edges)
        bmesh.ops.translate(bm, verts=filter_geom(ext['geom'], BMVert), vec=-face.normal * ((fd / 2) - eps))

def make_window_arch(bm, face, ares, aoff, aheight, **kwargs):
    """ Arc the top edge of a face """

    #bmesh.ops.inset_individual(bm, faces=[face], thickness= aheight / ares)
    # Get top edge
    top = sorted([e for e in face.edges], key=lambda ed: calc_edge_median(ed).z)[-1]

    # Subdivide
    ret = bmesh.ops.subdivide_edges(bm, edges=[top], cuts=ares)

    # Sort Verts
    verts = list({v for e in filter_geom(ret['geom_split'], BMEdge) for v in e.verts})
    if face.normal.y:
        verts.sort(key=lambda v: v.co.x)
    else:
        verts.sort(key=lambda v: v.co.y)

    # Offset verts along sin curve
    angle = pi / (len(verts)-1)
    for idx, v in enumerate(verts):
        off = sin(angle*idx) * aheight
        v.co.z -= aoff
        v.co.z += off

def make_window_arch_detail(bm, face, adetail, dthick, ddepth, **kwargs):
    """ Create detail in the arched face """

    if not adetail:
        return

    fn = face.normal
    # Poke face
    res = bmesh.ops.poke(bm, faces=[face])

    # inset and extrude
    if dthick > 0:
        ret = bmesh.ops.inset_individual(bm, faces=res['faces'], thickness=dthick)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

        ret = bmesh.ops.extrude_discrete_faces(bm, faces=res['faces'])
        verts = [v for f in ret['faces'] for v in f.verts]
        bmesh.ops.translate(bm, verts=verts, vec=-fn * ddepth)

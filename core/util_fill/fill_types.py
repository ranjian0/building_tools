import bpy
import bmesh
from mathutils import Vector
from bmesh.types import BMEdge, BMVert
from ...utils import (
        split,
        filter_geom,
        get_edit_mesh,
        filter_vertical_edges,
        filter_horizontal_edges
    )


def fill_panel(bm, face, panel_x, panel_y, panel_t, panel_d, **kwargs):
    """ Create panels on faace """

    # Create main panel to hold child panels
    bmesh.ops.inset_individual(bm,
        faces=[face], thickness=panel_t)

    # bmesh.ops.scale(bm,
    #     verts=list({v for e in face.edges for v in e.verts}),
    #     vec=(1, 1, gw))
    # bmesh.ops.translate(bm,
    #     verts=list({v for e in face.edges for v in e.verts}),
    #     vec=(0, 0, goff))

    # Calculate edges to be subdivided
    n = face.normal
    vedgs = filter_vertical_edges(face.edges, n)
    hedgs = list(set(face.edges) - set(vedgs))

    # Subdivide the edges
    res1 = bmesh.ops.subdivide_edges(bm,
        edges=vedgs,
        cuts=panel_x)

    res2 = bmesh.ops.subdivide_edges(bm,
        edges=hedgs + filter_geom(res1['geom_inner'], BMEdge),
        cuts=panel_y)

    # Get all panel faces
    vts = filter_geom(res2['geom_inner'], BMVert)
    faces = list(filter(lambda f: len(f.verts) == 4,
        {f for v in vts for f in v.link_faces if f.normal == n}))

    # Make panels
    bmesh.ops.inset_individual(bm, faces=faces, thickness=panel_t / 2)
    bmesh.ops.inset_individual(bm, faces=faces, thickness=panel_t / 2)
    bmesh.ops.translate(bm,
        verts=list({v for f in faces for v in f.verts}),
        vec=n * panel_d)

    # Clean geometry
    vts2 = [v for e in filter_geom(res1['geom_split'], BMEdge) for v in e.verts]
    vts2.sort(key=lambda v: v.co.z)
    vts2 = vts2[2:len(vts2) - 2]

    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0)
    bmesh.ops.dissolve_verts(bm, verts=list(set(vts + vts2)))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

def fill_glass_panes(bm, face, pane_x, pane_y, pane_t, pane_d, **kwargs):
    """ Create glass panes on face """

    n = face.normal
    v_edges = filter_vertical_edges(face.edges, n)
    h_edges = filter_horizontal_edges(face.edges, n)

    # -- if panes_x == 0, skip
    if pane_x:
        res1 = bmesh.ops.subdivide_edges(bm,
            edges=v_edges, cuts=pane_x).get('geom_inner')

    if pane_y:
        res2 = bmesh.ops.subdivide_edges(bm,
            edges=h_edges + filter_geom(res1, BMEdge) if pane_x else [],
            cuts=pane_y).get('geom_inner')

    # panes
    # -- if we're here successfully, about 3 things may have happened
    do_panes = True
    if pane_y:
        e = filter_geom(res2, BMEdge)
    else:
        if pane_x:
            e = filter_geom(res1, BMEdge)
        else:
            do_panes = False
    if do_panes:
        pane_faces = list({f for ed in e for f in ed.link_faces})
        panes = bmesh.ops.inset_individual(bm,
            faces=pane_faces, thickness=pane_t)

        for f in pane_faces:
            bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * pane_d)

def fill_louver(bm, face, **kwargs):
    pass

def fill_bars(bm, face, **kwargs):
    pass
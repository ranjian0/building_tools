import bpy
import bmesh
import itertools as it
from bmesh.types import (
    BMVert, BMFace, BMEdge
    )

from ...utils import (
    select,
    filter_geom,
    get_edit_mesh,
    )



def flr_multistorey(floor_count, floor_height, slab_thickness, slab_outset, **kwargs):
    """Create muti extrusions to resemble building floors

    Args:
        floor_count (int): Number of floors
        floor_height (float): Height of each floor
        slab_thickness (float): Thickness of floor slabs
        slab_outset (float): How much the slab extends outwards
    """
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    edges, del_faces = [], None
    if check_planar(bm):
        # -- find boundary edges
        edges = [e for e in bm.edges if e.is_boundary]
    else:
        # -- find boundary of selected faces
        del_faces = [f for f in bm.faces if f.select]
        all_edges = list({e for f in del_faces for e in f.edges})
        edges = [e for e in all_edges
                    if len(list({f.normal.to_tuple() for f in e.link_faces})) > 1]

    # --extrude floors
    slab_faces  = []
    offsets     = it.cycle([slab_thickness, floor_height])
    for offset in it.islice(offsets, 0, floor_count*2):
        ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
        bmesh.ops.translate(bm, vec=(0, 0, offset),
            verts=filter_geom(ext['geom'], bmesh.types.BMVert))

        edges = filter_geom(ext['geom'], bmesh.types.BMEdge)
        if offset == slab_thickness:
            slab_faces.extend(filter_geom(ext['geom'], bmesh.types.BMFace))

    bmesh.ops.inset_region(bm, faces=slab_faces, depth=-slab_outset)
    bmesh.ops.contextual_create(bm, geom=edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    if del_faces:
        bmesh.ops.delete(bm,
            geom=del_faces,
            context=3)
        select(list(bm.edges), False)

    bmesh.update_edit_mesh(me, True)


def check_planar(bm):
    """ Determine whether the bmesh contains only flat geometry """
    if len(list({v.co.z for v in bm.verts})) == 1:
        return True
    return False
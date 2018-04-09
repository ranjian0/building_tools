import bpy
import bmesh
import itertools as it
from bmesh.types import (
    BMVert, BMFace, BMEdge
    )

from ...utils import (
    get_edit_mesh,
    filter_geom,
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

    # -- find boundary edges
    edges = [e for e in bm.edges if e.is_boundary]

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
    bmesh.update_edit_mesh(me, True)

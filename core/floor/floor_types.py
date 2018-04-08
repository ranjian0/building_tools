import bpy
import bmesh
from bmesh.types import (
    BMVert, BMFace, BMEdge
    )

from ...utils import (
    get_edit_mesh
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

    # -- get active object bmesh
    bm = bmesh.from_edit_mesh(get_edit_mesh())

    # -- find boundary edges
    edges = [e for e in bm.edges if e.is_boundary]

    # -- extrude floor and slabs
    for i in range(floor_count):
        # Extrude slab
        slab_ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
        slab_faces = filter_geom(slab_ext['geom'], BMFace)
        verts = filter_geom(slab_ext['geom'], BMVert)
        edges = filter_geom(slab_ext['geom'], BMEdge)
        bmesh.ops.translate(bm, vec=(0, 0, slab_thickness), verts=verts)

        # Extrude floor
        floor_ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
        floor_faces = filter_geom(floor_ext['geom'], BMFace)
        verts = filter_geom(floor_ext['geom'], BMVert)
        edges = filter_geom(floor_ext['geom'], BMEdge)
        bmesh.ops.translate(bm, vec=(0, 0, floor_height), verts=verts)

        # Offset Slab
        ret = bmesh.ops.inset_region(bm, faces=slab_faces, depth=-slab_outset)

    # -- fill top face
    ret = bmesh.ops.contextual_create(bm, geom=edges)

    # -- update normals and mesh
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm_to_obj(bm, obj)


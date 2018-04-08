import bpy
import bmesh
from bmesh.types import (
    BMVert, BMFace, BMEdge
    )

from ...utils import (
    get_edit_mesh
    filter_geom,
    floor_mat_slab,
    floor_mat_wall,
    material_set_faces,
    )



def flr_multistorey(floor_count, floor_height, slab_thickness, slab_outset, **kwargs):
    """Create muti extrusions to resemble building floors

    Args:
        floor_count (int): Number of floors
        floor_height (float): Height of each floor
        slab_thickness (float): Thickness of floor slabs
        slab_outset (float): How much the slab extends outwards
    """

    # -- make/get materials
    slab_mat = kwargs.get("mat_slab")
    wall_mat = kwargs.get("mat_wall")
    if not slab_mat:
        slab_mat = floor_mat_slab(obj)
        obj.building.floors.mat_slab = slab_mat
    if not wall_mat:
        wall_mat = floor_mat_wall(obj)
        obj.building.floors.mat_wall = wall_mat

    mslab_faces, mfloor_faces = [], []

    # -- get active object bmesh
    bm = bmesh.from_edit_mesh(get_edit_mesh())

    # -- find boundary edges
    edges = [e for e in bm.edges if e.is_boundary]

    # -- floorplan faces are slab material
    mslab_faces.extend([f for f in bm.faces])

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

        # Material faces
        mslab_faces.extend(slab_faces+ret['faces'])
        mfloor_faces.extend(floor_faces)

    # -- fill top face
    ret = bmesh.ops.contextual_create(bm, geom=edges)
    mslab_faces.extend(ret['faces'])

    # Set materials
    unique = lambda lst : list(set(lst))
    material_set_faces(obj, slab_mat, unique(mslab_faces))
    material_set_faces(obj, wall_mat, unique(mfloor_faces))

    # -- update normals and mesh
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm_to_obj(bm, obj)


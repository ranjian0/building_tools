import bmesh
import itertools as it
from bmesh.types import BMVert, BMFace, BMEdge

from ...utils import select, filter_geom, set_material


def make_floors(
    bm, edges, floor_count, floor_height, slab_thickness, slab_outset, **kwargs
):
    """Create extrusions of floor geometry from a floorplan

    Args:
        bm (bmesh.types.BMesh): bmesh for the current editmesh
        edges (bmesh.types.BMEdgeSeq): bounding edges for editmesh (floorplan)
        floor_count  (int): Number of floors
        floor_height (float): Height of each floor
        slab_thickness (float): Thickness of floor slabs
        slab_outset (float): How much the slab extends outwards
        **kwargs: Extra kwargs from FloorProperty

    """
    del_faces = []
    if not edges:
        # -- find boundary of selected faces
        del_faces = [f for f in bm.faces if f.select]
        all_edges = list({e for f in del_faces for e in f.edges})
        edges = [
            e
            for e in all_edges
            if len(list({f for f in e.link_faces if f in del_faces})) == 1
        ]

    # --extrude floors
    slab_faces = []
    offsets = it.cycle([slab_thickness, floor_height])
    for offset in it.islice(offsets, 0, floor_count * 2):
        if offset == 0 and offset == slab_thickness:
            continue

        ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
        bmesh.ops.translate(
            bm, vec=(0, 0, offset), verts=filter_geom(ext["geom"], bmesh.types.BMVert)
        )

        edges = filter_geom(ext["geom"], bmesh.types.BMEdge)
        if offset == slab_thickness:
            slab_faces.extend(filter_geom(ext["geom"], bmesh.types.BMFace))

    res = bmesh.ops.inset_region(bm, faces=slab_faces, depth=-slab_outset)
    slab_faces.extend(res["faces"])
    bmesh.ops.contextual_create(bm, geom=edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    if del_faces:
        bmesh.ops.delete(bm, geom=del_faces, context="FACES")

    wall_faces = [f for f in bm.faces if f not in slab_faces and not f.normal.z]

    # -- setup materials for slab and wall faces
    set_material(slab_faces, "mat_slab")
    set_material(wall_faces, "mat_wall")

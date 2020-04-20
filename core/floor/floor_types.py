import bmesh
import functools as ft
from bmesh.types import BMVert, BMFace

from ...utils import (
    FaceMap,
    filter_geom,
    add_faces_to_map,
    extrude_face_region,
)


def create_floors(bm, faces, prop):
    """Create extrusions of floor geometry from a floorplan
    """
    slabs, walls = extrude_slabs_and_floors(bm, faces, prop)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    add_faces_to_map(bm, slabs, FaceMap.SLABS)
    add_faces_to_map(bm, walls, FaceMap.WALLS)


def extrude_slabs_and_floors(bm, faces, prop):
    """extrude edges alternating between slab and floor heights
    """
    slabs = []
    walls = []
    normal = faces[0].normal.copy()

    # extrude vertically
    if prop.add_slab:
        offsets = [prop.slab_thickness, prop.floor_height] * prop.floor_count
        for i, offset in enumerate(offsets):
            faces, surrounding_faces = extrude_face_region(bm, faces, offset, normal)
            if i%2:
                walls += surrounding_faces
            else:
                slabs += surrounding_faces
    else:
        offsets = [prop.floor_height] * prop.floor_count
        for offset in offsets:
            faces, surrounding_faces = extrude_face_region(bm, faces, offset, normal)
            walls += surrounding_faces

    # extrude slabs horizontally
    slabs = bmesh.ops.inset_region(
        bm, faces=slabs, depth=prop.slab_outset, use_even_offset=True, use_boundary=True)["faces"]

    return slabs, walls

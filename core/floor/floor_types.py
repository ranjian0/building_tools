import bmesh
from bmesh.types import BMFace

from ...utils import (
    FaceMap,
    filter_geom,
    add_faces_to_map,
    extrude_face_region,
    equal,
    filter_vertical_edges,
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

    faces = bmesh.ops.dissolve_faces(bm, faces=faces, use_verts=True)["region"]

    # extrude vertically
    if prop.add_slab:
        offsets = [prop.slab_thickness, prop.floor_height] * prop.floor_count
        for i, offset in enumerate(offsets):
            faces, surrounding_faces = extrude_face_region(bm, faces, offset, normal)
            if i==0:
                dissolve_flat_edges(bm, surrounding_faces)
                surrounding_faces = filter_geom(bmesh.ops.region_extend(bm, geom=faces, use_faces=True)["geom"], BMFace)
            if i%2:
                walls += surrounding_faces
            else:
                slabs += surrounding_faces

        # extrude slabs horizontally
        slabs = bmesh.ops.inset_region(
            bm, faces=slabs, depth=prop.slab_outset, use_even_offset=True, use_boundary=True)["faces"]

    else:
        offsets = [prop.floor_height] * prop.floor_count
        for i, offset in enumerate(offsets):
            faces, surrounding_faces = extrude_face_region(bm, faces, offset, normal)
            if i==0:
                dissolve_flat_edges(bm, surrounding_faces)
                surrounding_faces = filter_geom(bmesh.ops.region_extend(bm, geom=faces, use_faces=True)["geom"], BMFace)
            walls += surrounding_faces

    return slabs, walls


def dissolve_flat_edges(bm, faces):
    flat_edges = list({e for f in faces for e in filter_vertical_edges(f.edges, f.normal) if len(e.link_faces)>1 and equal(e.calc_face_angle(),0)})
    bmesh.ops.dissolve_edges(bm, edges=flat_edges, use_verts=True)

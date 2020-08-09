import bmesh
from bmesh.types import BMFace
from mathutils import Vector

from ...utils import (
    equal,
    FaceMap,
    filter_geom,
    closest_faces,
    add_faces_to_map,
    extrude_face_region,
    filter_vertical_edges,
    create_cube_without_faces,
)


def create_floors(bm, faces, prop):
    """Create extrusions of floor geometry from a floorplan
    """
    slabs, walls, roof = extrude_slabs_and_floors(bm, faces, prop)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    add_faces_to_map(bm, slabs, FaceMap.SLABS)
    add_faces_to_map(bm, walls, FaceMap.WALLS)
    add_faces_to_map(bm, roof, FaceMap.ROOF)


def extrude_slabs_and_floors(bm, faces, prop):
    """extrude edges alternating between slab and floor heights
    """
    slabs = []
    walls = []
    normal = faces[0].normal.copy()

    faces = bmesh.ops.dissolve_faces(bm, faces=faces)["region"]
    create_columns(bm, faces[-1], prop)

    # extrude vertically
    if prop.add_slab:
        offsets = [prop.slab_thickness, prop.floor_height] * prop.floor_count
        for i, offset in enumerate(offsets):
            if i == 0:
                orig_locs = [f.calc_center_bounds() for f in faces]
                flat_faces = get_flat_faces(faces, {})
                flat_faces, surrounding_faces = extrude_face_region(bm, flat_faces, offset, normal)
                dissolve_flat_edges(bm, surrounding_faces)
                surrounding_faces = filter_geom(bmesh.ops.region_extend(bm, geom=flat_faces, use_faces=True)["geom"], BMFace)
                faces = closest_faces(flat_faces, [l+Vector((0., 0., offset)) for l in orig_locs])
            else:
                faces, surrounding_faces = extrude_face_region(bm, faces, offset, normal)
            if i % 2:
                walls += surrounding_faces
            else:
                slabs += surrounding_faces

        # extrude slabs horizontally
        slabs += bmesh.ops.inset_region(
            bm, faces=slabs, depth=prop.slab_outset, use_even_offset=True, use_boundary=True)["faces"]

    else:
        offsets = [prop.floor_height] * prop.floor_count
        for i, offset in enumerate(offsets):
            faces, surrounding_faces = extrude_face_region(bm, faces, offset, normal)
            if i == 0:
                dissolve_flat_edges(bm, surrounding_faces)
                surrounding_faces = filter_geom(bmesh.ops.region_extend(bm, geom=faces, use_faces=True)["geom"], BMFace)
            walls += surrounding_faces

    return slabs, walls, faces


def dissolve_flat_edges(bm, faces):
    flat_edges = list({
        e for f in faces for e in filter_vertical_edges(f.edges)
        if len(e.link_faces) > 1 and equal(e.calc_face_angle(), 0)
    })
    bmesh.ops.dissolve_edges(bm, edges=flat_edges, use_verts=True)


def get_flat_faces(faces, visited):
    flat_edges = list({
        e for f in faces for e in f.edges
        if len(e.link_faces) > 1 and equal(e.calc_face_angle(), 0)
    })
    flat_faces = []
    for e in flat_edges:
        for f in e.link_faces:
            if not visited.get(f, False):
                visited[f] = True
                flat_faces += get_flat_faces([f], visited)
    return list(set(faces + flat_faces))


def create_columns(bm, face, prop):
    if not prop.add_columns:
        return

    res = []
    col_w = 2 * prop.slab_outset
    pos_h = prop.floor_height / 2 + (prop.slab_thickness if prop.add_slab else 0)
    for v in face.verts:
        for i in range(prop.floor_count):
            cube = create_cube_without_faces(
                bm, (col_w, col_w, prop.floor_height),
                (v.co.x, v.co.y, v.co.z + (pos_h * (i+1)) + ((prop.floor_height / 2) * i)), bottom=True)
            res.extend(cube.get("verts"))

    columns = list({f for v in res for f in v.link_faces})
    add_faces_to_map(bm, columns, FaceMap.COLUMNS)

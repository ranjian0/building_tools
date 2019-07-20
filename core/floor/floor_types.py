import bmesh
import itertools as it
import functools as ft
from bmesh.types import BMVert, BMEdge

from ...utils import (
    Material,
    filter_geom,
    set_material,
    boundary_edges_from_face_selection,
)


def create_floors(bm, edges, prop):
    """Create extrusions of floor geometry from a floorplan
    """
    start_height = 0.0
    faces_to_delete = []
    if edges is None:
        edges = boundary_edges_from_face_selection(bm)
        faces_to_delete = [f for f in bm.faces if f.select]
        start_height = faces_to_delete[-1].calc_center_median().z

    extrude_slabs_and_floors(bm, edges, prop)
    slabs, walls = get_slab_and_wall_faces(bm, prop, start_height)
    if prop.slab_outset > 0.0:
        result = bmesh.ops.inset_region(bm, faces=slabs, depth=-prop.slab_outset)
        slabs.extend(result["faces"])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if faces_to_delete:
        bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES")
    # create_floor_materials(slabs, walls)


def extrude_slabs_and_floors(bm, edges, prop):
    """extrude edges alternating between slab and floor heights
    """
    offsets = it.cycle([prop.slab_thickness, prop.floor_height])
    for offset in it.islice(offsets, 0, prop.floor_count * 2):
        if offset == 0:
            continue

        extrusion = bmesh.ops.extrude_edge_only(bm, edges=edges)
        bmesh.ops.translate(
            bm, vec=(0, 0, offset), verts=filter_geom(extrusion["geom"], BMVert)
        )
        edges = filter_geom(extrusion["geom"], BMEdge)
    bmesh.ops.contextual_create(bm, geom=edges)


def get_slab_and_wall_faces(bm, prop, start_height):
    """get faces that form slabs and walls
    """
    slabs, walls = [], []
    slab_heights, wall_heights = [], []
    for idx in range(prop.floor_count):
        slab_heights.append(
            prop.slab_thickness / 2
            + (idx * prop.slab_thickness)
            + (idx * prop.floor_height)
            + start_height
        )
        wall_heights.append(
            prop.floor_height / 2
            + (idx * prop.floor_height)
            + ((idx + 1) * prop.slab_thickness)
            + start_height
        )

    round_4dp = ft.partial(round, ndigits=4)
    for face in bm.faces:
        face_location_z = round_4dp(face.calc_center_median().z)
        if face_location_z in map(round_4dp, slab_heights):
            slabs.append(face)
        elif face_location_z in map(round_4dp, wall_heights):
            walls.append(face)
    return slabs, walls


def create_floor_materials(slab_faces, wall_faces):
    """add materials to floor faces
    """
    set_material(slab_faces, Material.SLAB)
    set_material(wall_faces, Material.WALL)

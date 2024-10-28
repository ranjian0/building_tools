import bmesh
import bpy
from bmesh.types import BMFace
from bmesh.types import BMVert
from mathutils import Vector

from ..materialgroup import MaterialGroup, add_faces_to_group
from ...utils import (
    equal,
    filter_geom,
    closest_faces,
    extrude_face_region,
    filter_vertical_edges,
    create_cube_without_faces,
    create_cube,
    create_plane,
    calc_verts_median,
    get_top_faces,
    get_bottom_edges,
    edge_vector,
    vec_equal,
    is_parallel
)


def create_floors(bm, faces, prop):
    """Create extrusions of floor geometry from a floorplan"""
    slabs, walls, roof = extrude_slabs_and_floors(bm, faces, prop)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    add_faces_to_group(bm, slabs, MaterialGroup.SLABS)
    add_faces_to_group(bm, walls, MaterialGroup.WALLS)
    add_faces_to_group(bm, roof, MaterialGroup.ROOF)


def extrude_slabs_and_floors(bm, faces, prop):
    """extrude edges alternating between slab and floor heights"""
    slabs = []
    walls = []
    normal = faces[0].normal.copy()

    if len(faces) > 1:
        faces = bmesh.ops.dissolve_faces(bm, faces=faces)["region"]
    create_columns(bm, faces[-1], prop)

    # extrude vertically
    if prop.add_slab:
        offsets = [prop.slab_thickness, prop.floor_height] * prop.floor_count
        for i, offset in enumerate(offsets):
            if i == 0:
                orig_locs = [f.calc_center_bounds() for f in faces]
                flat_faces = get_flat_faces(faces, {})
                flat_faces, surrounding_faces = extrude_face_region(
                    bm, flat_faces, offset, normal
                )
                dissolve_flat_edges(bm, surrounding_faces)
                surrounding_faces = filter_geom(
                    bmesh.ops.region_extend(bm, geom=flat_faces, use_faces=True)[
                        "geom"
                    ],
                    BMFace,
                )
                faces = closest_faces(
                    flat_faces, [l + Vector((0.0, 0.0, offset)) for l in orig_locs]
                )
            else:
                faces, surrounding_faces = extrude_face_region(
                    bm, faces, offset, normal
                )
            if i % 2:
                walls += surrounding_faces
            else:
                slabs += surrounding_faces

        # extrude slabs horizontally
        slabs += bmesh.ops.inset_region(
            bm,
            faces=slabs,
            depth=prop.slab_outset,
            use_even_offset=True,
            use_boundary=True,
        )["faces"]

    else:
        offsets = [prop.floor_height] * prop.floor_count
        for i, offset in enumerate(offsets):
            faces, surrounding_faces = extrude_face_region(bm, faces, offset, normal)
            if i == 0:
                dissolve_flat_edges(bm, surrounding_faces)
                surrounding_faces = filter_geom(
                    bmesh.ops.region_extend(bm, geom=faces, use_faces=True)["geom"],
                    BMFace,
                )
            walls += surrounding_faces

    return slabs, walls, faces


def dissolve_flat_edges(bm, faces):
    flat_edges = list(
        {
            e
            for f in faces
            for e in filter_vertical_edges(f.edges)
            if len(e.link_faces) > 1 and equal(e.calc_face_angle(), 0)
        }
    )
    bmesh.ops.dissolve_edges(bm, edges=flat_edges, use_verts=True)


def get_flat_faces(faces, visited):
    flat_edges = list(
        {
            e
            for f in faces
            for e in f.edges
            if len(e.link_faces) > 1 and equal(e.calc_face_angle(), 0)
        }
    )
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
    decoration_h = (prop.floor_height-prop.decoration_padding*(prop.decoration_nb - 1))/prop.decoration_nb
    decoration_padding = prop.decoration_padding
    decoration_nb = prop.decoration_nb

    col_w = 2 * prop.slab_outset 
    pos_h = prop.floor_height / 2 + (prop.slab_thickness if prop.add_slab else 0)
    
    center = calc_verts_median(face.verts)
    ref_vectors = []
    
    for v in face.verts:
        extrud_vectors=[]
        dir_vector = v.co - center
        dir_vector.x = dir_vector.x * prop.slab_outset/ (2*abs(dir_vector.x))
        dir_vector.y = dir_vector.y * prop.slab_outset/ (2*abs(dir_vector.y))
        for e in v.link_edges:
            if e.verts[0].index == v.index :
                extrud_vectors.append(edge_vector(e))
            else :
                extrud_vectors.append(-edge_vector(e))
        
        if is_parallel(extrud_vectors[0],extrud_vectors[1]):
            continue

        if len(ref_vectors) == 0:
            ref_vectors=[extrud_vectors[0],extrud_vectors[1]]
        
        
        for i in range(prop.floor_count):
            if not prop.add_decoration:
                cube = create_cube_without_faces(
                    bm,
                    (col_w, col_w, prop.floor_height),
                    (
                        v.co.x,
                        v.co.y,
                        v.co.z + (pos_h * (i + 1)) + ((prop.floor_height / 2) * i),
                    ),
                    bottom=True,
                )
                res.extend(cube.get("verts"))
            else:
                first_plane = create_plane(bm,(prop.slab_outset/2, prop.slab_outset/2),(
                        v.co.x+dir_vector.x,
                        v.co.y+dir_vector.y,
                        v.co.z + prop.slab_thickness
                    ))
                normal = face.normal.copy()
                first_face = bmesh.ops.contextual_create(bm, geom=first_plane.get("verts"))["faces"][0]
                next_face = get_top_faces([first_face])

                # determine which king of corner
                corner_type=0

                if is_parallel(extrud_vectors[0]+extrud_vectors[1],ref_vectors[0]+ref_vectors[1]) :
                    corner_type = 1
                
                for ii in range(decoration_nb):
                    sup_face, sides = extrude_face_region(bm,next_face,decoration_h,normal)
                    for _f in sides :
                        res.extend(_f.verts)
                    
                    for f_side in sides:
                        if vec_equal(f_side.normal,extrud_vectors[0]) or vec_equal(f_side.normal,extrud_vectors[1]):
                            
                            if vec_equal(f_side.normal,extrud_vectors[0]):
                                parity_index = (ii+corner_type)%2
                            else:
                                parity_index = (ii+corner_type+1)%2

                            if not prop.alternate_decoration :
                                parity_index = 1
                            #print(f'{ii}:{corner_type}:{parity_index}->{-prop.slab_outset*(1+prop.decoration_ratio*parity_index)}')
    
                            debug, debug2 = extrude_face_region(bm,[f_side],-prop.slab_outset*(1+prop.decoration_ratio*parity_index),f_side.normal)
                            
                    if (ii<decoration_nb-1):
                        next_face, sides = extrude_face_region(bm,sup_face,decoration_padding,normal)
                        sides, otherfaces = extrude_face_region(bm,sides,0,normal)
                            
                        for f in sides:
                            bmesh.ops.translate(bm, verts=f.verts, vec=f.normal * - decoration_padding)
                            res.extend(f.verts)
                    
    columns = list({f for v in res for f in v.link_faces})
    add_faces_to_group(bm, columns, MaterialGroup.COLUMNS)

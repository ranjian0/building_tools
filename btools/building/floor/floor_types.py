import bmesh
from bmesh.types import BMFace
from mathutils import Vector

from ...utils import (
    calc_verts_median,
    closest_faces,
    create_cube_without_faces,
    create_plane,
    edge_vector,
    equal,
    extrude_face_region,
    filter_geom,
    filter_vertical_edges,
    get_top_faces,
    is_parallel,
    offset_polygons,
    skeletonize,
    sweep_profile_along_edges,
    vec_equal,
)
from ..materialgroup import MaterialGroup, add_faces_to_group


def create_floors(bm, faces, prop):
    """Create extrusions of floor geometry from a floorplan"""
    slabs, walls, roof = extrude_slabs_and_floors(bm, faces, prop)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    add_faces_to_group(bm, slabs, MaterialGroup.SLABS)
    add_faces_to_group(bm, walls, MaterialGroup.WALLS)
    add_faces_to_group(bm, roof, MaterialGroup.ROOF)

    add_cornice(bm, prop)


def add_cornice(bm, prop):
    """String-course cornice band along every slab line (production-detail
    phase 4).

    A stepped molding profile is swept along the slab ring's top rim
    (already at the slab outset), projecting ``cornice_size`` further
    out and hanging below the seam. Runs are chained per building side
    (axis-aligned v1, like the gutter machinery) and oriented outward.
    Faces are tagged SLABS so they follow the concrete material slot.
    """
    if not getattr(prop, "add_cornice", False):
        return
    if not prop.add_slab:
        return  # cornices live on slab lines

    from ...utils import detail

    if not detail.detail_flag("cornice", detail.detail_level(), True):
        return

    layer = bm.faces.layers.int.get(".bt_material_group_index")
    if layer is None:
        return
    names = _matgroup_names()
    if "slabs" not in names:
        return
    slab_idx = names.index("slabs")

    size = prop.cornice_size
    step = prop.slab_thickness + prop.floor_height
    seam_z = lambda k: k * step + prop.slab_thickness

    center = calc_verts_median([v for f in bm.faces for v in f.verts])
    profile = [
        (0.0, 0.0),
        (size, 0.0),
        (size, -size * 0.45),
        (size * 0.55, -size * 0.45),
        (size * 0.55, -size * 0.7),
        (0.0, -size * 0.7),
    ]

    for k in range(1, prop.floor_count + 1):
        z = seam_z(k - 1) + prop.floor_height  # top of the k-th wall band
        rim = [
            e
            for e in bm.edges
            if abs(e.verts[0].co.z - z) < 1e-3
            and abs(e.verts[1].co.z - z) < 1e-3
            and any(f[layer] == slab_idx for f in e.link_faces)
        ]
        for run in _chain_axis_runs(rim).values():
            if len(run) < 1:
                continue
            mid = (run[0].verts[0].co + run[0].verts[1].co) / 2
            outward = mid - Vector((center.x, center.y, 0.0))
            run_dir = run[-1].verts[1].co - run[0].verts[0].co
            side = run_dir.cross(Vector((0.0, 0.0, 1.0)))
            flip = side.dot(outward) < 0
            faces = sweep_profile_along_edges(
                bm, run, profile, close_caps=True, side_flip=flip
            )
            add_faces_to_group(bm, faces, MaterialGroup.SLABS)


def _chain_axis_runs(edges, tol=0.05):
    """Bucket axis-aligned horizontal edges into straight runs per side
    (same bucketing idea as the roof gutter machinery)."""
    runs = {}
    for e in edges:
        d = e.verts[1].co - e.verts[0].co
        if abs(d.x) > 2 * abs(d.y):
            key = ("x", round(e.verts[0].co.y / tol))
        elif abs(d.y) > 2 * abs(d.x):
            key = ("y", round(e.verts[0].co.x / tol))
        else:
            continue
        runs.setdefault(key, []).append(e)
    for key, group in runs.items():
        axis_i = 0 if key[0] == "x" else 1
        group.sort(key=lambda e: min(e.verts[0].co[axis_i], e.verts[1].co[axis_i]))
    return runs


def _matgroup_names():
    import bpy

    obj = bpy.context.object
    return [mt.name for mt in getattr(obj, "bt_materials", [])]


def add_interior_shell(bm, prop):
    """Phase-1 interiors (#202): double-shell walls + per-storey floors.

    Call AFTER create_floors (the footprint is re-derived from the
    building's top face). The inner skin sits ``wall_thickness`` inward
    (exact mitered offset from the straight skeleton); one full-width
    floor face per storey is walkable and doubles as the storey ceiling
    below. The top face is untouched so roofs keep working.

    The api runs this in a NON-normalizing edit session: the skin is a
    disconnected component and a global recalc would reorient it away
    from the rooms; the ops path calls it after create_floors' recalc,
    and the skin orients itself explicitly here.
    """
    thickness = getattr(prop, "wall_thickness", 0.0)
    if thickness <= 0.0:
        return

    top_z = max(f.calc_center_median().z for f in bm.faces)
    cands = [
        f
        for f in bm.faces
        if f.normal.z > 0.9 and abs(f.calc_center_median().z - top_z) < 1e-4
    ]
    if not cands:
        return
    face = max(cands, key=lambda f: f.calc_area())

    contour = _face_contour(face)
    inner_walls, inner_floors = create_interior_shell(bm, contour, prop)
    if not inner_walls:
        return  # footprint too small for this thickness

    # -- the skin is disconnected from the shell: orient it toward the
    #    rooms explicitly (deterministic, independent of winding). Fresh
    #    faces carry stale normals until updated.
    bm.normal_update()
    tube_center = calc_verts_median([v for f in inner_walls for v in f.verts])
    for f in inner_walls:
        if (f.calc_center_median() - tube_center).dot(f.normal) > 0.0:
            f.normal_flip()

    add_faces_to_group(bm, inner_walls, MaterialGroup.WALLS)
    add_faces_to_group(bm, inner_floors, MaterialGroup.SLABS)


def _face_contour(face):
    """Clockwise (x, y) contour of a face via its loops (same ordering
    convention the straight skeleton requires)."""
    start = max(face.loops, key=lambda loop: loop.vert.co.to_tuple()[:2])
    contour = []
    loop = start
    for _ in range(len(face.loops)):
        contour.append((loop.vert.co.x, loop.vert.co.y))
        loop = loop.link_loop_prev
    return contour


def create_interior_shell(bm, contour, prop):
    """Inner wall tube + per-storey floor faces for a footprint contour."""
    skeleton = skeletonize(contour, [])
    rings = offset_polygons(skeleton, contour, prop.wall_thickness)
    if not rings:
        return [], []  # footprint too small for this thickness

    slab_t = prop.slab_thickness if prop.add_slab else 0.0
    step = slab_t + prop.floor_height
    inner_walls, inner_floors = [], []

    for ring in rings:
        # -- one continuous inner tube per offset ring, spanning all
        #    storey wall bands (the slab bands exist only as outset
        #    rings outside the footprint)
        n = len(ring)
        z0, z1 = slab_t, prop.floor_count * step
        bottom = [bm.verts.new((p.x, p.y, z0)) for p in ring]
        top = [bm.verts.new((p.x, p.y, z1)) for p in ring]
        for i in range(n):
            j = (i + 1) % n
            inner_walls.append(bm.faces.new((bottom[j], bottom[i], top[i], top[j])))

    for k in range(prop.floor_count):
        z = k * step + slab_t
        loop = [bm.verts.new((x, y, z)) for x, y in contour]
        inner_floors.append(bm.faces.new(reversed(loop)))

    return inner_walls, inner_floors


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
    decoration_h = (
        prop.floor_height - prop.decoration_padding * (prop.decoration_nb - 1)
    ) / prop.decoration_nb
    decoration_padding = prop.decoration_padding
    decoration_nb = prop.decoration_nb

    col_w = 2 * prop.slab_outset

    center = calc_verts_median(face.verts)
    ref_vectors = []

    # loop for each corner
    for v in face.verts:
        extrud_vectors = []
        dir_vector = v.co - center
        dir_vector.x = dir_vector.x * prop.slab_outset / (2 * abs(dir_vector.x))
        dir_vector.y = dir_vector.y * prop.slab_outset / (2 * abs(dir_vector.y))
        for e in v.link_edges:
            if e.verts[0].index == v.index:
                extrud_vectors.append(edge_vector(e))
            else:
                extrud_vectors.append(-edge_vector(e))

        if is_parallel(extrud_vectors[0], extrud_vectors[1]):
            continue

        if len(ref_vectors) == 0:
            ref_vectors = [extrud_vectors[0], extrud_vectors[1]]

        # loop for each floor
        for i in range(prop.floor_count):
            if not prop.add_decoration:
                col_w_i = col_w
                size = getattr(prop, "column_size", 0.0)
                if size and size > 0.0:
                    col_w_i = size  # decoupled from slab_outset
                z_base = (
                    v.co.z
                    + (prop.slab_thickness if prop.add_slab else 0.0) * (i + 1)
                    + i * prop.floor_height
                )
                shaft_h = prop.floor_height
                cap_h = 0.0
                if getattr(prop, "add_column_base", False) or getattr(
                    prop, "add_column_capital", False
                ):
                    cap_h = prop.column_cap_height
                    shaft_h = prop.floor_height - 2 * cap_h

                cube = create_cube_without_faces(
                    bm,
                    (col_w_i, col_w_i, shaft_h),
                    (v.co.x, v.co.y, z_base + shaft_h / 2),
                    bottom=True,
                )
                res.extend(cube.get("verts"))

                cap_w = col_w_i * prop.column_cap_size
                if getattr(prop, "add_column_base", False):
                    base = create_cube_without_faces(
                        bm,
                        (cap_w, cap_w, cap_h),
                        (v.co.x, v.co.y, z_base + cap_h / 2),
                        bottom=True,
                    )
                    res.extend(base.get("verts"))
                if getattr(prop, "add_column_capital", False):
                    cap = create_cube_without_faces(
                        bm,
                        (cap_w, cap_w, cap_h),
                        (v.co.x, v.co.y, z_base + shaft_h + cap_h + cap_h / 2),
                        bottom=True,
                    )
                    res.extend(cap.get("verts"))
            else:
                first_plane = create_plane(
                    bm,
                    (prop.slab_outset / 2, prop.slab_outset / 2),
                    (
                        v.co.x + dir_vector.x,
                        v.co.y + dir_vector.y,
                        v.co.z
                        + prop.slab_thickness * prop.add_slab * (i + 1)
                        + i * prop.floor_height,
                    ),
                )
                normal = face.normal.copy()
                first_face = bmesh.ops.contextual_create(
                    bm, geom=first_plane.get("verts")
                )["faces"][0]
                next_face = get_top_faces([first_face])

                # determine orientation (left or right) of corner
                corner_type = 0

                if is_parallel(
                    extrud_vectors[0] + extrud_vectors[1],
                    ref_vectors[0] + ref_vectors[1],
                ):
                    corner_type = 1

                # loop for decoration step
                for ii in range(decoration_nb):
                    sup_face, sides = extrude_face_region(
                        bm, next_face, decoration_h, normal
                    )
                    for _f in sides:
                        res.extend(_f.verts)

                    # extrude decorations
                    for f_side in sides:
                        if vec_equal(f_side.normal, extrud_vectors[0]) or vec_equal(
                            f_side.normal, extrud_vectors[1]
                        ):
                            if vec_equal(f_side.normal, extrud_vectors[0]):
                                parity_index = (ii + corner_type) % 2
                            else:
                                parity_index = (ii + corner_type + 1) % 2

                            if not prop.alternate_decoration:
                                parity_index = 1

                            extern_side, other_sides = extrude_face_region(
                                bm,
                                [f_side],
                                -prop.slab_outset
                                * (1 + prop.decoration_ratio * parity_index),
                                f_side.normal,
                            )

                            if (
                                ii < decoration_nb - 1
                            ) and not prop.alternate_decoration:
                                _, sides = extrude_face_region(
                                    bm,
                                    get_top_faces(other_sides),
                                    decoration_padding,
                                    normal,
                                )
                                sides, _ = extrude_face_region(bm, sides, 0, normal)
                                for f in sides:
                                    if not vec_equal(
                                        f.normal, extrud_vectors[0]
                                    ) and not vec_equal(f.normal, extrud_vectors[1]):
                                        if not is_parallel(
                                            f.normal, extern_side[0].normal
                                        ):
                                            bmesh.ops.translate(
                                                bm,
                                                verts=f.verts,
                                                vec=f.normal * -0.2 * prop.slab_outset,
                                            )
                                    else:
                                        if is_parallel(f.normal, extern_side[0].normal):
                                            bmesh.ops.translate(
                                                bm,
                                                verts=f.verts,
                                                vec=f.normal * -0.2 * prop.slab_outset,
                                            )

                    # padding decoration
                    if ii < decoration_nb - 1:
                        next_face, sides = extrude_face_region(
                            bm, sup_face, decoration_padding, normal
                        )
                        sides, _ = extrude_face_region(bm, sides, 0, normal)

                        for f in sides:
                            if not vec_equal(
                                f.normal, extrud_vectors[0]
                            ) and not vec_equal(f.normal, extrud_vectors[1]):
                                bmesh.ops.translate(
                                    bm,
                                    verts=f.verts,
                                    vec=f.normal * -0.2 * prop.slab_outset,
                                )
                            res.extend(f.verts)

    columns = list({f for v in res for f in v.link_faces})
    add_faces_to_group(bm, columns, MaterialGroup.COLUMNS)

import math

import bmesh
import mathutils
import numpy as np
from bmesh.types import BMFace, BMVert
from mathutils import Matrix, Vector

from ...utils import (
    calc_edge_median,
    edge_is_vertical,
    edge_vector,
    equal,
    filter_geom,
    popup_message,
    select,
    skeletonize,
    validate,
)
from ..materialgroup import (
    MaterialGroup,
    add_faces_to_group,
    add_material_group,
    map_new_faces,
)


def create_roof(bm, faces, prop):
    """Create roof types"""
    select(faces, False)
    if prop.type == "FLAT":
        create_flat_roof(bm, faces, prop)
    elif prop.type == "GABLE":
        add_material_group(MaterialGroup.ROOF_HANGS)
        create_gable_roof(bm, faces, prop)
    elif prop.type == "HIP":
        add_material_group(MaterialGroup.ROOF_HANGS)
        create_hip_roof(bm, faces, prop)

    # -- silhouette details
    if getattr(prop, "add_gutters", False):
        roof_faces = _roof_trim_faces(bm)
        if roof_faces:
            eave = _find_eave_edges(bm, roof_faces)
            add_gutters(bm, eave, radius=getattr(prop, "gutter_size", 0.08))
    if getattr(prop, "add_chimney", False):
        add_chimney(bm)
    if getattr(prop, "add_ridge_cap", False) and prop.type in ("GABLE", "HIP"):
        add_ridge_cap_and_verges(bm)


@map_new_faces(MaterialGroup.ROOF)
def create_flat_roof(bm, faces, prop):
    """Create a flat roof"""
    # -- extrude up and outset
    top_face = extrude_and_outset(bm, faces, prop.thickness, prop.outset)

    # -- add border
    if prop.add_border:
        # -- inset top face
        bmesh.ops.inset_region(
            bm, faces=top_face, thickness=prop.border, use_even_offset=True
        )

        # -- extrude downwards
        ret = bmesh.ops.extrude_face_region(bm, geom=top_face).get("geom")
        bmesh.ops.translate(
            bm, vec=(0, 0, -(prop.thickness - 0.0011)), verts=filter_geom(ret, BMVert)
        )
        bmesh.ops.delete(bm, geom=top_face, context="FACES")

        # -- chamfer the coping ring's top edges
        coping = getattr(prop, "coping_size", 0.02)
        if coping > 0.001:
            top_z = max(v.co.z for v in bm.verts)
            edges = [
                e
                for e in bm.edges
                if abs(e.verts[0].co.z - top_z) < 0.01
                and abs(e.verts[1].co.z - top_z) < 0.01
            ]
            if edges:
                bmesh.ops.bevel(
                    bm,
                    geom=edges,
                    offset=coping,
                    offset_type="OFFSET",
                    segments=1,
                    profile=0.5,
                    affect="EDGES",
                    clamp_overlap=True,
                )


def create_gable_roof(bm, faces, prop):
    """Create gable roof"""
    # -- create initial outset for box gable roof
    if prop.gable_type == "BOX":
        faces = extrude_and_outset(bm, faces, prop.thickness, prop.outset)
        link_faces = {f for fa in faces for e in fa.edges for f in e.link_faces}
        all_edges = {e for f in link_faces for e in f.edges}
        bmesh.ops.delete(bm, geom=list(link_faces), context="FACES")
        faces = bmesh.ops.contextual_create(bm, geom=validate(all_edges)).get("faces")

        bot_faces = [f for e in faces[-1].edges for f in e.link_faces if f not in faces]
        add_faces_to_group(bm, bot_faces, MaterialGroup.ROOF_HANGS)
    else:
        # -- Open GABLE
        #  XXX prevent dissolve_lone_verts from destroying lower geometry
        ret = bmesh.ops.extrude_face_region(bm, geom=faces).get("geom")
        bmesh.ops.translate(bm, vec=(0, 0, 0.0011), verts=filter_geom(ret, BMVert))
        bmesh.ops.delete(bm, geom=faces, context="FACES")
        faces = filter_geom(ret, BMFace)

    # -- dissolve if faces are many
    if len(faces) > 1:
        faces = bmesh.ops.dissolve_faces(bm, faces=faces, use_verts=True).get("region")
    face = faces[-1]
    median = face.calc_center_median()

    # -- remove verts that are between two parallel edges
    dissolve_lone_verts(bm, face, list(face.edges))
    original_edges = validate(face.edges)

    # -- get verts in anti-clockwise order (required by straight skeleton)
    verts = [v for v in sort_verts_by_loops(face)]
    points = [v.co.to_tuple()[:2] for v in verts]

    # -- compute straight skeleton
    skeleton = skeletonize(points, [], zero_gradient=True)
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    height_scale = prop.height / max([arc.height for arc in skeleton])

    # -- create edges and vertices
    skeleton_edges = create_skeleton_verts_and_edges(
        bm, skeleton, original_edges, median, height_scale
    )

    # -- create faces
    roof_faces = create_skeleton_faces(bm, original_edges, skeleton_edges)
    if prop.gable_type == "OPEN":
        gable_process_open(bm, roof_faces, prop)
    elif prop.gable_type == "BOX":
        gable_process_box(bm, roof_faces, prop)


def create_hip_roof(bm, faces, prop):
    """Create a hip roof"""
    # -- create base for hip roof
    roof_hang = map_new_faces(MaterialGroup.ROOF_HANGS)(extrude_and_outset)
    faces = roof_hang(bm, faces, prop.thickness, prop.outset)
    face = faces[-1]
    median = face.calc_center_median()

    # -- remove verts that are between two parallel edges
    dissolve_lone_verts(bm, face, list(face.edges))
    original_edges = validate(face.edges)

    # -- get verts in anti-clockwise order
    verts = [v for v in sort_verts_by_loops(face)]
    points = [v.co.to_tuple()[:2] for v in verts]

    # -- compute straight skeleton
    skeleton = skeletonize(points, [])
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    height_scale = prop.height / max([arc.height for arc in skeleton])

    # -- create edges and vertices
    skeleton_edges = create_skeleton_verts_and_edges(
        bm, skeleton, original_edges, median, height_scale
    )

    # -- create faces
    create_skeleton_faces(bm, original_edges, skeleton_edges)


def sort_verts_by_loops(face):
    """sort verts in face clockwise using loops"""
    start_loop = max(face.loops, key=lambda loop: loop.vert.co.to_tuple()[:2])

    verts = []
    current_loop = start_loop
    while len(verts) < len(face.loops):
        verts.append(current_loop.vert)
        current_loop = current_loop.link_loop_prev

    return verts


def vert_at_loc(loc, verts, loc_z=None):
    """Find all verts at loc(x,y), return the one with highest z coord"""
    results = []
    for vert in verts:
        co = vert.co
        if equal(co.x, loc.x) and equal(co.y, loc.y):
            if loc_z:
                if equal(co.z, loc_z):
                    results.append(vert)
            else:
                results.append(vert)

    if results:
        return max([v for v in results], key=lambda v: v.co.z)
    return None


def create_skeleton_verts_and_edges(bm, skeleton, original_edges, median, height_scale):
    """Create the vertices and edges from output of straight skeleton"""
    skeleton_edges = []
    skeleton_verts = []
    O_verts = list({v for e in original_edges for v in e.verts})
    for arc in skeleton:
        source = arc.source
        vsource = vert_at_loc(source, O_verts + skeleton_verts)
        if not vsource:
            source_height = [arc.height for arc in skeleton if arc.source == source]
            ht = source_height.pop() * height_scale
            vsource = make_vert(bm, Vector((source.x, source.y, median.z + ht)))
            skeleton_verts.append(vsource)

        for sink in arc.sinks:
            vs = vert_at_loc(sink, O_verts + skeleton_verts)
            if not vs:
                sink_height = min([arc.height for arc in skeleton if sink in arc.sinks])
                ht = height_scale * sink_height
                vs = make_vert(bm, Vector((sink.x, sink.y, median.z + ht)))
            skeleton_verts.append(vs)

            # create edge
            if vs != vsource:
                geom = bmesh.ops.contextual_create(bm, geom=[vsource, vs]).get("edges")
                skeleton_edges.extend(geom)

    skeleton_edges = validate(skeleton_edges)
    S_verts = list({v for e in skeleton_edges for v in e.verts} - set(O_verts))
    return join_intersections_and_get_skeleton_edges(bm, S_verts, skeleton_edges)


@map_new_faces(MaterialGroup.ROOF)
def create_skeleton_faces(bm, original_edges, skeleton_edges):
    """Create faces formed from hiproof verts and edges"""

    def interior_angle(vert, e1, e2):
        """Determine anti-clockwise interior angle between edges
        https://stackoverflow.com/questions/2827393/angles-between-two-n-dimensional-vectors-in-python
        """
        # XXX Order of vector creation is really important
        v1 = vert.co - e1.other_vert(vert).co
        v2 = e2.other_vert(vert).co - vert.co
        return np.arctan2(np.linalg.det([v1.xy, v2.xy]), np.dot(v1.xy, v2.xy))

    def boundary_walk(e, reverse=False):
        """Perform boundary walk using least interior angle"""
        v, last = e.verts
        if reverse:
            last, v = e.verts

        previous = e
        found_edges = [e]
        while v != last:
            linked = [
                e for e in v.link_edges if e in skeleton_edges and e not in found_edges
            ]
            if not linked:
                common_edge = set(v.link_edges) & set(last.link_edges)
                if common_edge:
                    found_edges.append(common_edge.pop())
                    break
                # Re-walk if we have not reversed already, otherwise fail quietly
                return boundary_walk(e, True) if not reverse else []

            next_edge = linked[0]
            if len(linked) > 1:
                next_edge = min(linked, key=lambda e: interior_angle(v, previous, e))
            previous = next_edge
            found_edges.append(next_edge)
            v = next_edge.other_vert(v)

        return found_edges

    result = []
    for ed in validate(original_edges):
        walk = boundary_walk(ed)
        if len(walk) < 3:
            # XXX Geometry error caused by intersecting roof edges
            # esp when outset property is set high on concave polygons

            # -- try to help user
            popup_message(
                "Roof Intersection Detected. Adjust(decrease) roof 'outset'",
                title="Geometry Error",
            )
            continue
        result.extend(bmesh.ops.contextual_create(bm, geom=walk).get("faces"))
    return result


def make_vert(bm, location):
    """Create a vertex at location"""
    return bmesh.ops.create_vert(bm, co=location).get("vert").pop()


def join_intersecting_verts_and_edges(bm, edges, verts):
    """Find all vertices that intersect/ lie at an edge and merge
    them to that edge
    """
    eps = 0.0001
    new_verts = []
    for v in verts:
        for e in edges:
            if v in e.verts:
                continue

            v1, v2 = e.verts
            ortho = edge_vector(e).orthogonal().normalized() * eps
            res = mathutils.geometry.intersect_line_line_2d(v.co, v.co, v1.co, v2.co)
            if res is None:
                res = mathutils.geometry.intersect_line_line_2d(
                    v.co - ortho, v.co + ortho, v1.co, v2.co
                )

            if res:
                split_vert = v1
                split_factor = (v1.co - v.co).length / e.calc_length()
                _, new_vert = bmesh.utils.edge_split(e, split_vert, split_factor)
                new_verts.append(new_vert)
    return validate(new_verts)


def get_linked_edges(verts, filter_edges):
    """Find all the edges linked to verts that are also in filter edges"""
    linked_edges = [e for v in verts for e in v.link_edges]
    return list(filter(lambda e: e in filter_edges, linked_edges))


def find_closest_pair_edges(edges_a, edges_b):
    """Find the edges in edges_a and edges_b that are closest to each other"""

    def length_func(pair):
        e1, e2 = pair
        return (calc_edge_median(e1) - calc_edge_median(e2)).length

    pairs = [(e1, e2) for e1 in edges_a for e2 in edges_b]
    return sorted(pairs, key=length_func)[0]


def join_intersections_and_get_skeleton_edges(bm, skeleton_verts, skeleton_edges):
    """Join intersecting edges and verts and return all edges that are in skeleton_edges"""
    new_verts = join_intersecting_verts_and_edges(bm, skeleton_edges, skeleton_verts)
    skeleton_verts = validate(skeleton_verts) + new_verts
    bmesh.ops.remove_doubles(bm, verts=skeleton_verts, dist=0.0001)
    return list(set(e for v in validate(skeleton_verts) for e in v.link_edges))


def dissolve_lone_verts(bm, face, original_edges):
    """Find all verts only connected to two edges and dissolve them"""
    loops = {loop for v in face.verts for loop in v.link_loops if loop.face == face}

    def is_parallel(loop):
        return round(loop.calc_angle(), 2) == 3.14

    parallel_verts = [loop.vert for loop in loops if is_parallel(loop)]
    lone_edges = [
        e for v in parallel_verts for e in v.link_edges if e not in original_edges
    ]
    bmesh.ops.dissolve_edges(bm, edges=lone_edges, use_verts=True)


def gable_process_box(bm, roof_faces, prop):
    """Finalize box gable roof type"""
    # -- extrude upward faces
    top_faces = [f for f in roof_faces if f.normal.z]
    result = bmesh.ops.extrude_face_region(bm, geom=top_faces).get("geom")

    # -- move abit upwards (by amount roof thickness)
    bmesh.ops.translate(
        bm, verts=filter_geom(result, BMVert), vec=(0, 0, prop.thickness)
    )
    bmesh.ops.delete(bm, geom=top_faces, context="FACES")

    # -- face maps
    link_faces = {
        f
        for fc in filter_geom(result, BMFace)
        for e in fc.edges
        for f in e.link_faces
        if not f.normal.z
    }
    link_faces.update(set(validate(roof_faces)))
    add_faces_to_group(bm, list(link_faces), MaterialGroup.ROOF_HANGS)


def gable_process_open(bm, roof_faces, prop):
    """Finalize open gable roof type"""
    add_faces_to_group(bm, roof_faces, MaterialGroup.WALLS)

    # -- find only the upward facing faces
    top_faces = [f for f in roof_faces if f.normal.z]

    # -- extrude and move up
    result = bmesh.ops.extrude_face_region(bm, geom=top_faces).get("geom")
    bmesh.ops.translate(
        bm, verts=filter_geom(result, BMVert), vec=(0, 0, prop.thickness)
    )
    bmesh.ops.delete(bm, geom=top_faces, context="FACES")

    # -- find newly created side faces
    side_faces = []
    new_faces = filter_geom(result, BMFace)
    for e in [ed for f in new_faces for ed in f.edges]:
        link_faces = e.link_faces
        len_valid = len(link_faces) == 2
        link_valid = sum([f in new_faces for f in link_faces]) == 1

        if len_valid and link_valid:
            side_faces.extend(set(link_faces) - set(new_faces))

    # --determine upper bounding edges to be dissolved after outset
    dissolve_edges = []
    for f in side_faces:
        v_edges = list(filter(edge_is_vertical, f.edges))
        edges = list(set(f.edges) - set(v_edges))
        max_edge = max(edges, key=lambda e: calc_edge_median(e).z)
        dissolve_edges.append(max_edge)

    # -- outset side faces
    bmesh.ops.inset_region(
        bm, use_even_offset=True, faces=side_faces, depth=prop.outset
    )

    # -- move lower vertical edges abit down (inorder to maintain roof slope)
    v_edges = []
    for f in side_faces:
        v_edges.extend(list(filter(edge_is_vertical, f.edges)))

    # -- find ones with lowest z
    min_z = min([calc_edge_median(e).z for e in v_edges])
    min_z_edges = [e for e in v_edges if calc_edge_median(e).z == min_z]
    min_z_verts = list(set(v for e in min_z_edges for v in e.verts))
    bmesh.ops.translate(bm, verts=min_z_verts, vec=(0, 0, -prop.outset / 2))

    # -- post cleanup
    bmesh.ops.dissolve_edges(bm, edges=dissolve_edges)

    # -- matgroups
    linked = {f for fc in side_faces for e in fc.edges for f in e.link_faces}
    linked_top = [f for f in linked if f.normal.z > 0]
    linked_bot = [f for f in linked if f.normal.z < 0]
    add_faces_to_group(bm, linked_top, MaterialGroup.ROOF)
    add_faces_to_group(bm, side_faces + linked_bot, MaterialGroup.ROOF_HANGS)


def add_ridge_cap_and_verges(bm, cap_width=0.14, cap_height=0.05, board=0.06):
    """Ridge cap along the roof's highest edge + verge boards on raking
    edges of gable slopes (both tagged ROOF via the map_new_faces wrapper
    of create_roof's callers)."""
    from ...utils import sweep_profile_along_edges

    roof_faces = _roof_trim_faces(bm)
    if not roof_faces:
        return
    max_z = max(v.co.z for f in roof_faces for v in f.verts)
    min_z = min(v.co.z for f in roof_faces for v in f.verts)

    ridge, rakes = [], []
    for f in roof_faces:
        for e in f.edges:
            z0, z1 = e.verts[0].co.z, e.verts[1].co.z
            if abs(z0 - max_z) < 0.01 and abs(z1 - max_z) < 0.01:
                ridge.append(e)
            elif (
                abs(z0 - max_z) < 0.01
                and abs(z1 - min_z) < 0.01
                or abs(z1 - max_z) < 0.01
                and abs(z0 - min_z) < 0.01
            ):
                rakes.append(e)

    ridge = validate(ridge)
    if ridge:
        cap = [
            (-cap_width / 2, -0.02),
            (0.0, cap_height),
            (cap_width / 2, -0.02),
        ]
        faces = sweep_profile_along_edges(bm, ridge, cap, close_caps=True)
        add_faces_to_group(bm, faces, MaterialGroup.ROOF)

    rakes = validate(rakes)
    if rakes:
        board_profile = [
            (-board / 2, -board * 0.4),
            (board / 2, -board * 0.4),
            (board / 2, board * 0.8),
            (-board / 2, board * 0.8),
        ]
        for e in rakes:
            faces = sweep_profile_along_edges(bm, [e], board_profile)
            add_faces_to_group(bm, faces, MaterialGroup.ROOF)


def extrude_and_outset(bm, faces, thickness, outset):
    """Extrude the given faces upwards and outset resulting side faces"""
    # -- extrude faces upwards
    ret = bmesh.ops.extrude_face_region(bm, geom=faces)
    bmesh.ops.translate(
        bm, vec=(0, 0, thickness), verts=filter_geom(ret["geom"], BMVert)
    )

    # -- dissolve top faces if they are more than one
    top_face = filter_geom(ret["geom"], BMFace)
    if len(top_face) > 1:
        top_face = (
            bmesh.ops.dissolve_faces(bm, faces=top_face, use_verts=True)
            .get("region")
            .pop()
        )
    else:
        top_face = top_face.pop()

    # -- outset the side faces from earlier extrusion
    link_faces = [f for e in top_face.edges for f in e.link_faces if f is not top_face]
    bmesh.ops.inset_region(bm, faces=link_faces, depth=outset, use_even_offset=True)

    # -- cleanup hidden faces
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.delete(bm, geom=faces, context="FACES")

    new_faces = list({f for e in top_face.edges for f in e.link_faces})
    return bmesh.ops.dissolve_faces(bm, faces=new_faces).get("region")


def _roof_trim_faces(bm):
    """Faces belonging to the ROOF or ROOF_HANGS material groups.

    The layer stores the OBJECT's material-item index (generation order),
    not the enum value -- resolve the wanted indices via bt_materials.
    """
    import bpy

    layer = bm.faces.layers.int.get(".bt_material_group_index")
    if layer is None:
        return []
    obj = bpy.context.object
    names = [mt.name for mt in getattr(obj, "bt_materials", [])]
    wanted = {names.index(n) for n in ("roof", "roof_hangs") if n in names}
    return [f for f in bm.faces if f[layer] in wanted]


def _find_eave_edges(bm, roof_faces):
    """Find horizontal edges at the lowest z of the given roof face set."""
    min_z = min(v.co.z for f in roof_faces for v in f.verts)
    eave = [
        e
        for e in bm.edges
        if abs(e.verts[0].co.z - min_z) < 0.01 and abs(e.verts[1].co.z - min_z) < 0.01
    ]
    return eave


def _run_direction(axis, edges):
    """Overall direction of a chained run along its axis (+1 / -1 oriented
    by the bucket sort); unit vector."""
    d = 1.0
    if edges:
        a, b = edges[0].verts[0].co, edges[-1].verts[1].co
        if (b - a)[0 if axis == "x" else 1] < 0:
            d = -1.0
    return Vector((d, 0, 0)) if axis == "x" else Vector((0, d, 0))


def _chain_runs(edges, tol=0.05):
    """Bucket axis-aligned edges into straight runs by (axis, lateral pos).

    Returns {("x", lateral): [edges sorted along x]}, ... for both axes.
    """
    buckets = {}
    for e in edges:
        d = e.verts[1].co - e.verts[0].co
        # -- skip diagonal (mitred corner) edges: not gutter runs
        if abs(d.x) > 2 * abs(d.y):
            axis, lat = "x", 1
        elif abs(d.y) > 2 * abs(d.x):
            axis, lat = "y", 0
        else:
            continue
        mid = (e.verts[0].co + e.verts[1].co) / 2
        key = (axis, round(mid[lat] / tol))
        buckets.setdefault(key, []).append(e)
    runs = {}
    for key, group in buckets.items():
        axis = key[0]
        lat_i = 1 if axis == "x" else 0
        group.sort(key=lambda e: min(e.verts[0].co[lat_i], e.verts[1].co[lat_i]))
        runs[key] = group
    return runs


def add_gutters(bm, eave_edges, radius=0.04):
    """Half-round gutters hung below the eave edges (tagged ROOF_HANGS).

    Edges are chained into one straight run per building side; each tube
    hangs fully OUTSIDE the eave line so it never intersects the wall
    faces behind the trim.
    """
    from ...utils import sweep_profile_along_edges

    if not eave_edges:
        return

    center = Vector(
        (
            sum(v.co.x for e in eave_edges for v in e.verts) / (2 * len(eave_edges)),
            sum(v.co.y for e in eave_edges for v in e.verts) / (2 * len(eave_edges)),
            0.0,
        )
    )

    # -- slope facing directions: gutters belong only on EAVE sides (where
    #    a roof slope drains toward the edge); gable/rake ends are skipped
    eave_dirs = []
    for f in _roof_trim_faces(bm):
        n = f.normal
        h = Vector((n.x, n.y, 0.0))
        if 0.15 < abs(n.z) < 0.97 and h.length > 0.1:
            eave_dirs.append(h.normalized())

    r = radius
    # -- tube hangs fully BELOW the eave line (a top lip above it grazes
    #    the wall tops at corners)
    profile = [
        (0.15 * r, -0.01),
        (0.15 * r, -r * 0.6),
        (0.45 * r, -r),
        (1.1 * r, -r * 1.2),
        (1.75 * r, -r),
        (2.1 * r, -r * 0.6),
        (2.1 * r, -0.01),
    ]

    # -- wall extent per axis: gutter runs must not reach past the walls
    #    into the rake/outset corners (gable end walls sliver there)
    import bpy as _bpy

    _obj = _bpy.context.object
    _names = [mt.name for mt in getattr(_obj, "bt_materials", [])]
    _layer = bm.faces.layers.int.get(".bt_material_group_index")
    wall_lo, wall_hi = {}, {}
    if _layer is not None:
        wi = {i for i, n in enumerate(_names) if n == "walls"}
        wverts = [v.co for f in bm.faces if f[_layer] in wi for v in f.verts]
        if wverts:
            wall_lo = {"x": min(v.x for v in wverts), "y": min(v.y for v in wverts)}
            wall_hi = {"x": max(v.x for v in wverts), "y": max(v.y for v in wverts)}

    runs = _chain_runs(eave_edges)
    filtered = {}
    for (axis, lat), run_edges in runs.items():
        if axis in wall_lo:
            ai = 0 if axis == "x" else 1
            lo, hi = wall_lo[axis] - 0.02, wall_hi[axis] + 0.02
            trimmed = [
                e
                for e in run_edges
                if lo <= min(e.verts[0].co[ai], e.verts[1].co[ai])
                and max(e.verts[0].co[ai], e.verts[1].co[ai]) <= hi
            ]
            if not trimmed:
                continue
            run_edges = trimmed
        filtered[(axis, lat)] = run_edges

    for (axis, lat), run_edges in filtered.items():
        lat_i = 1 if axis == "x" else 0
        first, last = run_edges[0], run_edges[-1]
        mid = (first.verts[0].co + last.verts[1].co) / 2
        mid[lat_i] = first.verts[0].co[lat_i]
        run_dir = _run_direction(axis, run_edges)
        side = Vector((run_dir.y, -run_dir.x, 0.0))
        to_center = center - mid
        flip = side.dot(to_center) > 0  # side must point AWAY from center
        outward = -side if flip else side
        # -- eave check: a slope must drain toward this side
        if not any(d.dot(outward) > 0.5 for d in eave_dirs):
            continue
        faces = sweep_profile_along_edges(
            bm, run_edges, profile, close_caps=True, side_flip=flip
        )
        add_faces_to_group(bm, faces, MaterialGroup.ROOF_HANGS)


def add_chimney(bm, roof_faces=None, width=0.45, depth=0.45, height=1.2):
    """Masonry chimney stack rising from a roof slope (tagged ROOF)."""
    import bmesh
    from mathutils import Vector

    if roof_faces is None:
        roof_faces = _roof_trim_faces(bm)
    slopes = [
        f for f in roof_faces if f.calc_area() > 1.0 and 0.15 < abs(f.normal.z) < 0.97
    ]
    if slopes:
        slope = max(slopes, key=lambda f: f.calc_area())
        c = slope.calc_center_median()
        n = slope.normal.copy()
    else:
        # -- flat fallback: center of the roof top
        tops = [f for f in roof_faces if f.normal.z > 0.9]
        if not tops:
            return
        slope = max(tops, key=lambda f: f.calc_area())
        c = slope.calc_center_median()
        n = Vector((0.0, 0.0, 1.0))

    base = c - n * 0.2  # sink into the slope
    ret = bmesh.ops.create_cube(
        bm,
        size=1.0,
        matrix=Matrix.Translation(base + Vector((0, 0, height / 2)))
        @ Matrix.Scale(width, 4, Vector((1, 0, 0)))
        @ Matrix.Scale(depth, 4, Vector((0, 1, 0)))
        @ Matrix.Scale(height + 0.4, 4, Vector((0, 0, 1))),
    )
    add_faces_to_group(
        bm, [f for v in ret["verts"] for f in v.link_faces], MaterialGroup.ROOF
    )

    # -- flue pot (octagonal cylinder) on the stack top
    pot_r = 0.08
    pot_h = 0.25
    segs = 8
    top_z = base.z + height + 0.4
    ring_bottom, ring_top = [], []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        ring_bottom.append(
            bm.verts.new((c.x + pot_r * math.cos(a), c.y + pot_r * math.sin(a), top_z))
        )
        ring_top.append(
            bm.verts.new(
                (
                    c.x + pot_r * math.cos(a),
                    c.y + pot_r * math.sin(a),
                    top_z + pot_h,
                )
            )
        )
    pot_faces = []
    for i in range(segs):
        j = (i + 1) % segs
        pot_faces.append(
            bm.faces.new((ring_bottom[i], ring_bottom[j], ring_top[j], ring_top[i]))
        )
    pot_faces.append(bm.faces.new(ring_top))  # cap
    add_faces_to_group(bm, pot_faces, MaterialGroup.ROOF)

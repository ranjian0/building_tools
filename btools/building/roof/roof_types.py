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
    from ...utils import detail

    level = detail.detail_level()
    if not detail.detail_flag("ridge_cap", level, True):
        prop.add_ridge_cap = False
    if not detail.detail_flag("chimney", level, True):
        prop.add_chimney = False
    if not detail.detail_flag("gutters", level, True):
        prop.add_gutters = False

    select(faces, False)
    if prop.type == "FLAT":
        create_flat_roof(bm, faces, prop)
    elif prop.type == "GABLE":
        add_material_group(MaterialGroup.ROOF_HANGS)
        create_gable_roof(bm, faces, prop)
    elif prop.type == "HIP":
        add_material_group(MaterialGroup.ROOF_HANGS)
        create_hip_roof(bm, faces, prop)
    elif prop.type == "FLAT_TOP":
        add_material_group(MaterialGroup.ROOF_HANGS)
        create_flat_top_roof(bm, faces, prop)
    elif prop.type == "MANSARD":
        add_material_group(MaterialGroup.ROOF_HANGS)
        create_mansard_roof(bm, faces, prop)
    elif prop.type == "HALF_HIP":
        add_material_group(MaterialGroup.ROOF_HANGS)
        create_half_hip_roof(bm, faces, prop)

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


def slope_to_height_scale(prop, max_arc_height):
    """Uniform height multiplier (skeleton time -> Z) for the slope mode.

    HEIGHT      -> tallest arc reaches prop.height (original behavior)
    ANGLE       -> tan(slope_angle): every plane rises at the given pitch
    PERCENTAGE  -> rise/run as a fraction (100% = 45 degrees)
    """
    if prop.slope_mode == "ANGLE":
        return math.tan(prop.slope_angle)
    if prop.slope_mode == "PERCENTAGE":
        return prop.slope_percentage / 100.0
    return prop.height / max_arc_height


def resolve_edge_weights(prop, edge_count):
    """Parse the edge_weights option into skeleton weights.

    Accepts a comma-separated pitch string ("45,30,45,30", degrees) or a
    sequence of pitches; values cycle when fewer than edge_count are given.
    Returns tan(pitch) weights, or None when unset.
    """
    raw = getattr(prop, "edge_weights", None)
    if not raw:
        return None
    if isinstance(raw, str):
        values = [float(v) for v in raw.strip("[]() ").replace(",", " ").split()]
    else:
        values = [float(v) for v in raw]
    if not values:
        return None
    return [math.tan(math.radians(values[i % len(values)])) for i in range(edge_count)]


def _prepare_skeleton_base(bm, faces):
    """Dissolve the base into one face and clean its outline.

    Returns (faces, median, original_edges, points) with points in the
    clockwise order the straight skeleton requires."""
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
    return faces, median, original_edges, points


def build_skeleton_roof(bm, faces, prop, zero_gradient=False):
    """Shared skeleton-roof pipeline (hip/gable and derived styles).

    Lifts every skeleton arc by ``arc.height * scale`` where ``scale``
    resolves from the slope mode (height / angle / percentage). With
    per-edge weights (edge_weights option), arc heights already are roof
    heights (w = tan of pitch) and no scale is applied.

    Returns (skeleton, original_edges, roof_faces, median) for the callers'
    finishing passes."""
    faces, median, original_edges, points = _prepare_skeleton_base(bm, faces)

    # -- compute straight skeleton
    weights = resolve_edge_weights(prop, len(points))
    skeleton = skeletonize(points, [], zero_gradient=zero_gradient, weights=weights)
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    if weights is not None:
        height_fn = lambda arc: arc.height
    else:
        max_height = max(arc.height for arc in skeleton)
        scale = slope_to_height_scale(prop, max_height)
        height_fn = lambda arc, s=scale: arc.height * s

    # -- create edges and vertices
    skeleton_edges = create_skeleton_verts_and_edges(
        bm, skeleton, original_edges, median, height_fn
    )

    # -- create faces
    roof_faces = create_skeleton_faces(bm, original_edges, skeleton_edges)
    return skeleton, original_edges, roof_faces, median


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

    _, _, roof_faces, _ = build_skeleton_roof(bm, faces, prop, zero_gradient=True)
    if prop.gable_type == "OPEN":
        gable_process_open(bm, roof_faces, prop)
    elif prop.gable_type == "BOX":
        gable_process_box(bm, roof_faces, prop)


def create_hip_roof(bm, faces, prop):
    """Create a hip roof"""
    # -- create base for hip roof
    roof_hang = map_new_faces(MaterialGroup.ROOF_HANGS)(extrude_and_outset)
    faces = roof_hang(bm, faces, prop.thickness, prop.outset)
    build_skeleton_roof(bm, faces, prop)


def _half_hip_weights(points, base_weight, ridge_fraction):
    """Weights for a half-hip (jerkinhead) roof.

    Edges perpendicular to the footprint's long axis (the roof "ends")
    get a steeper pitch so their wavefronts cut in less and the ridge
    runs longer than a full hip: ridge = L - W * (1 - ridge_fraction),
    with ridge_fraction 0 = full hip and -> 1 approaching a gable.
    """
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    axis_x = (max(xs) - min(xs)) >= (max(ys) - min(ys))
    axis = Vector((1.0, 0.0)) if axis_x else Vector((0.0, 1.0))
    end_scale = 1.0 / max(1.0 - ridge_fraction, 0.05)
    n = len(points)
    weights = []
    for i in range(n):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        d = Vector((x1 - x0, y1 - y0))
        if d.length == 0.0:
            weights.append(base_weight)
            continue
        is_end = abs(d.normalized().dot(axis)) < 0.5
        weights.append(base_weight * end_scale if is_end else base_weight)
    return weights


def create_half_hip_roof(bm, faces, prop):
    """Create a half-hip (jerkinhead) roof: a hip whose end faces are
    steepened so the ridge runs longer (ridge_fraction 0 = hip)."""
    # -- create base for the roof
    roof_hang = map_new_faces(MaterialGroup.ROOF_HANGS)(extrude_and_outset)
    faces = roof_hang(bm, faces, prop.thickness, prop.outset)
    faces, median, original_edges, points = _prepare_skeleton_base(bm, faces)

    n_edges = len(points)
    per_edge = resolve_edge_weights(prop, n_edges)
    if per_edge is not None:
        weights = per_edge
    else:
        # -- main pitch from the slope mode (over an unweighted probe)
        probe = skeletonize(points, [])
        base_weight = slope_to_height_scale(prop, max(arc.height for arc in probe))
        weights = _half_hip_weights(points, base_weight, prop.ridge_fraction)

    skeleton = skeletonize(points, [], weights=weights)
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")
    skeleton_edges = create_skeleton_verts_and_edges(
        bm, skeleton, original_edges, median, lambda arc: arc.height
    )
    create_skeleton_faces(bm, original_edges, skeleton_edges)


def _pt_key(p):
    return (round(p.x, 6), round(p.y, 6))


def _truncate_skeleton(skeleton, base_points, cap_t, scale):
    """Cut a straight skeleton at time ``cap_t`` (flat-top roofs).

    Arcs above the cut are dropped; arcs crossing it are shortened to their
    level-set crossing point. Returns (segments, heights, rings):

    - segments: [(Vector2, Vector2)] surviving edges
    - heights: {pt_key: absolute Z} for every kept point and crossing
    - rings: [[Vector2]] closed cap rings (crossings around each
      above-cut component, ordered around their centroid)
    """
    # -- outline points sit at the base (height 0); Subtree.height is the
    #    SOURCE's height, so sinks on the outline must not inherit it.
    #    Skeleton points are float32 Vectors while the contour is float64,
    #    so match by distance rather than exact keys.
    base_vecs = [Vector((float(x), float(y))) for x, y in base_points]

    def on_base(p):
        for v in base_vecs:
            if (p - v).length <= 1e-5:
                return True
        return False

    sink_h = {}
    for arc in skeleton:
        for s in arc.sinks:
            k = _pt_key(s)
            if on_base(s):
                sink_h[k] = 0.0
            else:
                sink_h[k] = min(sink_h.get(k, math.inf), arc.height)
    source_h = {_pt_key(arc.source): arc.height for arc in skeleton}

    high = set()
    for arc in skeleton:
        if arc.height > cap_t:
            high.add(_pt_key(arc.source))
        for s in arc.sinks:
            if sink_h[_pt_key(s)] > cap_t:
                high.add(_pt_key(s))

    # -- connected components of the above-cut point graph
    adj = {k: set() for k in high}
    for arc in skeleton:
        ks = _pt_key(arc.source)
        for s in arc.sinks:
            ksnk = _pt_key(s)
            if ks in high and ksnk in high:
                adj[ks].add(ksnk)
                adj[ksnk].add(ks)
    comp_of, comps = {}, []
    for k in high:
        if k in comp_of:
            continue
        cid = len(comps)
        comps.append([])
        stack = [k]
        comp_of[k] = cid
        while stack:
            u = stack.pop()
            comps[cid].append(u)
            for w in adj[u]:
                if w not in comp_of:
                    comp_of[w] = cid
                    stack.append(w)

    def crossing(src, snk, t_src, t_snk):
        f = (cap_t - t_snk) / (t_src - t_snk)
        return snk + (src - snk) * f

    segments = []
    heights = {}
    ring_pts = [[] for _ in comps]
    cap_z = cap_t * scale

    for arc in skeleton:
        t_src = source_h[_pt_key(arc.source)]
        for s in arc.sinks:
            t_snk = sink_h[_pt_key(s)]
            if t_src > cap_t and t_snk > cap_t:
                continue  # fully above the cut
            if t_src <= cap_t and t_snk <= cap_t:
                segments.append((arc.source, s))
                heights.setdefault(_pt_key(arc.source), t_src * scale)
                heights.setdefault(_pt_key(s), t_snk * scale)
            elif t_src > cap_t:
                c = crossing(arc.source, s, t_src, t_snk)
                segments.append((c, s))
                heights.setdefault(_pt_key(s), t_snk * scale)
                heights.setdefault(_pt_key(c), cap_z)
                ring_pts[comp_of[_pt_key(arc.source)]].append(c)
            else:
                c = crossing(arc.source, s, t_src, t_snk)
                segments.append((arc.source, c))
                heights.setdefault(_pt_key(arc.source), t_src * scale)
                heights.setdefault(_pt_key(c), cap_z)
                ring_pts[comp_of[_pt_key(s)]].append(c)

    rings = []
    for pts in ring_pts:
        if len(pts) < 3:
            continue
        cx = sum(p.x for p in pts) / len(pts)
        cy = sum(p.y for p in pts) / len(pts)
        pts.sort(key=lambda p: math.atan2(p.y - cy, p.x - cx))
        rings.append(pts)
    return segments, heights, rings


def _build_truncated_skeleton_mesh(
    bm, segments, rings, heights, original_edges, median
):
    """Mesh a truncated skeleton: segments + cap rings.

    Returns (skeleton_edges, ring_verts) with ring edges included in the
    edge graph so the boundary walk in create_skeleton_faces closes the
    slope faces against the cap ring."""
    skeleton_edges = []
    skeleton_verts = []
    O_verts = list({v for e in original_edges for v in e.verts})

    def vert_for(p):
        v = vert_at_loc(p, O_verts + skeleton_verts)
        if not v:
            z = heights[_pt_key(p)]
            v = make_vert(bm, Vector((p.x, p.y, median.z + z)))
            skeleton_verts.append(v)
        return v

    for p1, p2 in segments:
        v1, v2 = vert_for(p1), vert_for(p2)
        if v1 == v2:
            continue
        geom = bmesh.ops.contextual_create(bm, geom=[v1, v2]).get("edges")
        skeleton_edges.extend(geom)

    ring_verts = []
    for ring in rings:
        rvs = [vert_for(p) for p in ring]
        for i in range(len(rvs)):
            skeleton_edges.append(bm.edges.new((rvs[i], rvs[(i + 1) % len(rvs)])))
        ring_verts.append(rvs)

    skeleton_edges = validate(skeleton_edges)
    S_verts = list({v for e in skeleton_edges for v in e.verts} - set(O_verts))
    return join_intersections_and_get_skeleton_edges(
        bm, S_verts, skeleton_edges
    ), ring_verts


def create_flat_top_roof(bm, faces, prop):
    """Create a flat-top (truncated hip) roof"""
    # -- create base for the roof
    roof_hang = map_new_faces(MaterialGroup.ROOF_HANGS)(extrude_and_outset)
    faces = roof_hang(bm, faces, prop.thickness, prop.outset)

    faces, median, original_edges, points = _prepare_skeleton_base(bm, faces)

    # -- compute straight skeleton
    skeleton = skeletonize(points, [])
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    max_height = max(arc.height for arc in skeleton)
    scale = slope_to_height_scale(prop, max_height)
    cap = min(prop.flat_height, max_height * scale)

    segments, heights, rings = _truncate_skeleton(skeleton, points, cap / scale, scale)
    skeleton_edges, ring_verts = _build_truncated_skeleton_mesh(
        bm, segments, rings, heights, original_edges, median
    )
    roof_faces = create_skeleton_faces(bm, original_edges, skeleton_edges)

    # -- cap faces over the truncation rings
    for rvs in ring_verts:
        rvs = validate(rvs)
        if len(rvs) >= 3:
            f = bm.faces.new(rvs)
            if f is not None:
                add_faces_to_group(bm, [f], MaterialGroup.ROOF)
    return roof_faces


def _ring_edges(ring_verts):
    """Boundary edges connecting consecutive ring verts (post-join)."""
    edges = []
    n = len(ring_verts)
    for i in range(n):
        a, b = ring_verts[i], ring_verts[(i + 1) % n]
        shared = set(a.link_edges) & set(b.link_edges)
        if not shared:
            raise ValueError("ring verts not connected by an edge")
        edges.append(shared.pop())
    return edges


def create_mansard_roof(bm, faces, prop):
    """Create a mansard roof: steep lower band up to a break ring, hip tier
    above it (reuses the flat-top truncation machinery)."""
    # -- create base for the roof
    roof_hang = map_new_faces(MaterialGroup.ROOF_HANGS)(extrude_and_outset)
    faces = roof_hang(bm, faces, prop.thickness, prop.outset)

    faces, median, original_edges, points = _prepare_skeleton_base(bm, faces)

    # -- compute straight skeleton
    skeleton = skeletonize(points, [])
    bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")

    max_height = max(arc.height for arc in skeleton)
    lower_scale = slope_to_height_scale(prop, max_height)
    apex_z = max_height * lower_scale
    break_z = min(prop.lower_height, apex_z)

    segments, heights, rings = _truncate_skeleton(
        skeleton, points, break_z / lower_scale, lower_scale
    )
    skeleton_edges, ring_verts = _build_truncated_skeleton_mesh(
        bm, segments, rings, heights, original_edges, median
    )

    # -- lower band faces first: while no upper-tier edges exist, the
    #    boundary walks cannot leave the lower band
    create_skeleton_faces(bm, original_edges, skeleton_edges)

    if break_z >= apex_z - 1e-6:
        # -- break at/above the apex: degenerate upper tier, cap instead
        for rvs in ring_verts:
            rvs = validate(rvs)
            if len(rvs) >= 3:
                f = bm.faces.new(rvs)
                if f is not None:
                    add_faces_to_group(bm, [f], MaterialGroup.ROOF)
        return

    for rvs in ring_verts:
        rvs = validate(rvs)
        if len(rvs) < 3:
            continue
        rvs = rvs[::-1]  # rings come out CCW; the skeleton wants CW
        try:
            ring_edges = _ring_edges(rvs)
        except ValueError:
            continue
        ring_points = [(v.co.x, v.co.y) for v in rvs]

        upper_skeleton = skeletonize(ring_points, [])
        upper_max = max(arc.height for arc in upper_skeleton)
        upper_scale = prop.upper_height / upper_max
        base = Vector((0.0, 0.0, median.z + break_z))
        upper_edges = create_skeleton_verts_and_edges(
            bm,
            upper_skeleton,
            ring_edges,
            base,
            lambda arc, s=upper_scale: arc.height * s,
        )
        create_skeleton_faces(bm, ring_edges, upper_edges)


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


def create_skeleton_verts_and_edges(bm, skeleton, original_edges, median, height_fn):
    """Create the vertices and edges from output of straight skeleton.

    height_fn(arc) gives the absolute Z lift for an arc's source point;
    sink points take the minimum over the arcs that contain them."""
    skeleton_edges = []
    skeleton_verts = []
    O_verts = list({v for e in original_edges for v in e.verts})
    for arc in skeleton:
        source = arc.source
        vsource = vert_at_loc(source, O_verts + skeleton_verts)
        if not vsource:
            source_height = [height_fn(a) for a in skeleton if a.source == source]
            ht = source_height.pop()
            vsource = make_vert(bm, Vector((source.x, source.y, median.z + ht)))
            skeleton_verts.append(vsource)

        for sink in arc.sinks:
            vs = vert_at_loc(sink, O_verts + skeleton_verts)
            if not vs:
                ht = min(height_fn(a) for a in skeleton if sink in a.sinks)
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

    # -- cleanup hidden faces (scoped: a blanket recalc reorients
    #    disconnected components such as interior skins)
    from ...utils import recalc_face_normals_component

    recalc_face_normals_component(bm, [top_face])
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

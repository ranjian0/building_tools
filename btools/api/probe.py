"""Semantic geometry probes for built objects.

Measurement-first validation: instead of interpreting rendered pixels,
probes query the mesh directly -- where feature groups sit, how they
align, whether they interpenetrate -- and can render text projections
(ASCII elevations) that agents without vision can read as plain output.

All functions are headless-safe (bmesh + mathutils only, no bpy.ops) and
return JSON-serializable data or plain text.
"""

import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from .validate import MATGROUP_LAYER, matgroup_counts

# deterministic char palette for ASCII views (index = sorted group order)
_PALETTE = "#+*=oOx@%&$DWBFRTPSLCQUEAVHGKMNXYZIJ123456789"

_VIEWS = {
    # view:  (ray direction, u axis, v axis)
    "front": (Vector((0, 1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))),
    "back": (Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))),
    "right": (Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))),
    "left": (Vector((1, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, 1))),
    "top": (Vector((0, 0, -1)), Vector((1, 0, 0)), Vector((0, 1, 0))),
    "iso": (
        Vector((-1, 1, -1)).normalized(),
        Vector((1, 0.35, 0)).normalized(),
        Vector((0, 0, 1)),
    ),
}


def _load(obj):
    """(bm, {group_name: [BMFace]}); bm must be freed by the caller."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.index_update()
    names = [mt.name for mt in getattr(obj, "bt_materials", [])]
    layer = bm.faces.layers.int.get(MATGROUP_LAYER)
    groups: dict = {}
    if layer is not None:
        for f in bm.faces:
            gi = f[layer]
            if gi < 0:
                continue
            name = names[gi] if gi < len(names) else "invalid_%d" % gi
            groups.setdefault(name, []).append(f)
    return bm, groups


def _cluster(values, tol):
    """Cluster sorted scalars; returns [[min, max, [vals]]...] groups."""
    out = []
    for v in sorted(values):
        if out and v - out[-1][1] <= tol:
            out[-1][1] = v
            out[-1][2].append(v)
        else:
            out.append([v, v, [v]])
    return out


def _bbox(verts):
    pts = [v.co if hasattr(v, "co") else v for v in verts]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


# ------------------------------------------------------------- measurements


def storey_bands(obj, tol=0.25):
    """Vertical storey bands from geometry.

    Uses slab-group face centers when present (one band per slab), else
    falls back to the overall z range as a single band.
    Returns [{"z": band_center, "base": band_min, "top": band_max}] sorted.
    """
    bm, groups = _load(obj)
    try:
        faces = groups.get("slabs")
        if faces:
            zs = [f.calc_center_median().z for f in faces]
        else:
            zs = [v.co.z for gfaces in groups.values() for f in gfaces for v in f.verts]
            if not zs:
                return []
            return [{"z": (min(zs) + max(zs)) / 2, "base": min(zs), "top": max(zs)}]
        bands = []
        for c in _cluster(zs, tol):
            bands.append({"z": sum(c[2]) / len(c[2]), "base": c[0], "top": c[1]})
        return bands
    finally:
        bm.free()


def counts_per_storey(obj, group, bands=None):
    """{storey_label: face_count} for a group, banded by storey_bands().

    Faces are assigned to the nearest band by center z (walls/slabs
    outside all bands are ignored). Labels: "storey_0", "storey_1", ...
    from the bottom.
    """
    bands = bands if bands is not None else storey_bands(obj)
    if not bands:
        return {}
    bm, groups = _load(obj)
    try:
        centers = [f.calc_center_median().z for f in groups.get(group, [])]
    finally:
        bm.free()
    counts = {}
    for z in centers:
        band_i = min(
            range(len(bands)), key=lambda i: abs(bands[i]["z"] - z), default=None
        )
        if band_i is None:
            continue
        # only count faces reasonably near their band (within 1.5 storeys)
        if abs(bands[band_i]["z"] - z) > 2.0:
            continue
        counts.setdefault("storey_%d" % band_i, 0)
        counts["storey_%d" % band_i] += 1
    return counts


def _elevation_filter(obj, groups, faces, depth_axis, near_negative):
    """Faces belonging to one elevation of the building.

    Anchors on the dominant wall PLANE for the elevation (the walls-group
    bbox is polluted by protruding features tagged as walls, e.g. balcony
    sides). Outsets up to 1.2m -- 1m balcony platforms -- still count.
    """
    if not faces:
        return []
    axis_i = {"x": 0, "y": 1, "z": 2}[depth_axis]

    # -- the outermost wall plane facing the viewer
    best = None
    for p in wall_planes(obj, "walls"):
        n = p["normal"]
        if abs(n[axis_i]) < 0.9:
            continue
        facing_viewer = n[axis_i] < 0 if near_negative else n[axis_i] > 0
        if not facing_viewer:
            continue
        best = n[axis_i] * p["d"]  # plane point along the depth axis
        break  # wall_planes is sorted by face count: first match wins

    if best is None:  # no wall plane facing the viewer: give up cleanly
        return []

    band = (best - 1.2, best + 0.6) if near_negative else (best - 0.6, best + 1.2)
    return [f for f in faces if band[0] <= f.calc_center_median()[axis_i] <= band[1]]


def elevation_bays(obj, group, view="front", tol=0.2):
    """Column clusters of a group's faces on one elevation.

    Projects face centers onto the view's horizontal axis and clusters
    them into bays. Returns [{"center", "min", "max", "count", "z_min",
    "z_max"}] sorted by center.
    """
    if view not in _VIEWS:
        raise ValueError("unknown view %r (have: %s)" % (view, sorted(_VIEWS)))
    _, u_axis, _ = _VIEWS[view]
    depth_axis = {"front": "y", "back": "y", "right": "x", "left": "x"}.get(view)
    bm, groups = _load(obj)
    try:
        faces = groups.get(group, [])
        if depth_axis is not None:
            faces = _elevation_filter(
                obj, groups, faces, depth_axis, view in ("front", "left")
            )
        us = [f.calc_center_median().dot(u_axis) for f in faces]
        bays = []
        for c in _cluster(us, tol):
            cfaces = [f for f, u in zip(faces, us) if c[0] - 1e-9 <= u <= c[1] + 1e-9]
            zs = [v.co.z for f in cfaces for v in f.verts]
            bays.append(
                {
                    "center": sum(c[2]) / len(c[2]),
                    "min": c[0],
                    "max": c[1],
                    "count": len(c[2]),
                    "z_min": min(zs) if zs else None,
                    "z_max": max(zs) if zs else None,
                }
            )
        return bays
    finally:
        bm.free()


def wall_planes(obj, group="walls", tol=0.05):
    """Domininant planes of a group's faces.

    Clusters faces by (rounded normal, rounded plane offset); returns
    [{"normal": [x,y,z], "d": plane_offset, "count"}] sorted by count.
    """
    bm, groups = _load(obj)
    try:
        planes = {}
        for f in groups.get(group, []):
            n = f.normal
            d = sum(v.co.dot(n) for v in f.verts) / len(f.verts)
            key = (round(n.x, 2), round(n.y, 2), round(n.z, 2), round(d, 2))
            rec = planes.setdefault(key, {"n": n.copy(), "ds": [], "count": 0})
            rec["ds"].append(d)
            rec["count"] += 1
        out = []
        for key, rec in planes.items():
            if rec["count"] < 2:
                continue
            n = rec["n"]
            d = sum(rec["ds"]) / len(rec["ds"])
            out.append(
                {"normal": [n.x, n.y, n.z], "d": round(d, 4), "count": rec["count"]}
            )
        return sorted(out, key=lambda p: -p["count"])[:12]
    finally:
        bm.free()


def group_protrusions(obj, group="frame", planes_group="walls"):
    """How far a group's geometry extends past each wall plane.

    For every dominant wall plane (outward normal n, offset d), the
    protrusion is max over the group's verts of (v.n - d). A window sill
    shows up as ~0.075 on the front/back planes; buried geometry reads ~0.
    Returns [{"normal", "d", "protrusion"}].
    """
    bm, groups = _load(obj)
    try:
        gfaces = groups.get(group, [])
        out = []
        for p in wall_planes(obj, planes_group):
            n = Vector(p["normal"])
            best = 0.0
            for f in gfaces:
                for v in f.verts:
                    best = max(best, v.co.dot(n) - p["d"])
            out.append(
                {"normal": p["normal"], "d": p["d"], "protrusion": round(best, 4)}
            )
        return out
    finally:
        bm.free()


def border_outsets(obj, group="roof"):
    """Per-side extents of a group's bbox beyond the wall planes (plan).

    Anchors on dominant wall PLANES, not the walls-group bbox: protruding
    features tagged as walls (balcony sides) would otherwise pollute the
    reference and fake asymmetry.
    """
    # -- outermost wall plane per horizontal direction
    # outermost extents: the -axis extreme is the MIN anchor among planes
    # facing -axis, the +axis extreme is the MAX among +facing planes
    # (internal back-facing planes must not win)
    anchors = {"x": ([], []), "y": ([], [])}
    for p in wall_planes(obj, "walls"):
        n = p["normal"]
        for axis_i, axis in ((0, "x"), (1, "y")):
            if abs(n[axis_i]) < 0.9:
                continue
            anchors[axis][0 if n[axis_i] < 0 else 1].append(n[axis_i] * p["d"])
    try:
        wx0, wx1 = min(anchors["x"][0]), max(anchors["x"][1])
        wy0, wy1 = min(anchors["y"][0]), max(anchors["y"][1])
    except ValueError:
        return {}

    bm, groups = _load(obj)
    try:
        gverts = [v for f in groups.get(group, []) for v in f.verts]
        if not gverts:
            return {}
        (gx0, gx1), (gy0, gy1), _ = _bbox(gverts)
        return {
            "x_min": round(gx0 - wx0, 4),
            "x_max": round(gx1 - wx1, 4),
            "y_min": round(gy0 - wy0, 4),
            "y_max": round(gy1 - wy1, 4),
        }
    finally:
        bm.free()


# --------------------------------------------------------- intersections


def _group_tree_polygons(obj, group):
    """(vertices, polygons, groups_per_polygon) for one matgroup."""
    bm, groups = _load(obj)
    try:
        faces = groups.get(group, [])
        verts, polys = [], []
        for f in faces:
            base = len(verts)
            verts.extend(v.co.copy() for v in f.verts)
            polys.append(list(range(base, base + len(f.verts))))
        return verts, polys
    finally:
        bm.free()


def _triangulate(poly, verts):
    """Fan-triangulate a polygon (index list) into (i0, i1, i2) triples."""
    return [(poly[0], poly[i], poly[i + 1]) for i in range(1, len(poly) - 1)]


def _seg_tri_cross(p0, p1, tri, verts, eps=1e-9, shrink=0.94):
    """True when segment p0-p1 properly crosses triangle (coplanar and
    boundary grazes excluded via a shrunk test triangle)."""
    (i0, i1, i2) = tri
    v0, v1, v2 = verts[i0], verts[i1], verts[i2]
    if shrink < 1.0:
        cen = (v0 + v1 + v2) / 3
        v0 = cen + (v0 - cen) * shrink
        v1 = cen + (v1 - cen) * shrink
        v2 = cen + (v2 - cen) * shrink
    e1, e2 = v1 - v0, v2 - v0
    d = p1 - p0
    n = e1.cross(e2)
    denom = n.dot(d)
    if abs(denom) < eps:  # parallel/coplanar: touching, not crossing
        return False
    t = n.dot(v0 - p0) / denom
    if t < eps or t > 1 - eps:
        return False
    h = p0 + d * t - v0
    u, v = e1.dot(h), e2.dot(h)
    # barycentric (u, v) via 2x2 solve on the triangle's parametric plane
    det = e1.dot(e1) * e2.dot(e2) - (e1.dot(e2)) ** 2
    if abs(det) < eps:
        return False
    uu, vv = e1.dot(e1), e2.dot(e2)
    uv = e1.dot(e2)
    bu = (uu * v - uv * u) / det
    bv = (vv * u - uv * v) / det
    return bu >= -eps and bv >= -eps and bu + bv <= 1 + eps


def _face_edges(f):
    """[(va, vb)] vertex-coordinate pairs for a bmesh face's edges."""
    return [(e.verts[0].co, e.verts[1].co) for e in f.edges]


def group_intersections(obj, group_a, group_b, max_crossings=50):
    """Count proper edge-triangle crossings between two matgroups.

    Exact geometry (no closed-volume assumptions, immune to ray-parity
    leaks on open meshes and to coplanar touching): a crossing needs an
    edge of one group to pierce a triangle of the other with vertices on
    both sides. Counting stops early at max_crossings (bounded runtime);
    the boolean answer is what matters.
    """
    bm, groups = _load(obj)
    try:
        faces_a = groups.get(group_a, [])
        faces_b = groups.get(group_b, [])
        if not faces_a or not faces_b:
            return 0

        # -- group B as a triangle soup + global bbox for broad-phase
        verts_b, tris_b = [], []
        for f in faces_b:
            base = len(verts_b)
            verts_b.extend(v.co.copy() for v in f.verts)
            poly = list(range(base, base + len(f.verts)))
            tris_b.extend(_triangulate(poly, verts_b))
        if not tris_b:
            return 0
        bverts_flat = [verts_b[i] for t in tris_b for i in t]
        bb_lo = Vector(
            (
                min(v.x for v in bverts_flat),
                min(v.y for v in bverts_flat),
                min(v.z for v in bverts_flat),
            )
        )
        bb_hi = Vector(
            (
                max(v.x for v in bverts_flat),
                max(v.y for v in bverts_flat),
                max(v.z for v in bverts_flat),
            )
        )

        crossings = 0
        for f in faces_a:
            c = f.calc_center_median()
            r = max((v.co - c).length for v in f.verts)
            if (
                c.x - r > bb_hi.x
                or c.x + r < bb_lo.x
                or c.y - r > bb_hi.y
                or c.y + r < bb_lo.y
                or c.z - r > bb_hi.z
                or c.z + r < bb_lo.z
            ):
                continue  # A face nowhere near B: skip its edges
            for p0, p1 in _face_edges(f):
                for t in tris_b:
                    if _seg_tri_cross(p0, p1, t, verts_b):
                        crossings += 1
                        if crossings >= max_crossings:
                            return crossings
        return crossings
    finally:
        bm.free()


def intersection_report(obj, pairs):
    """Proper-interpenetration counts for matgroup pairs.

    pairs: list of [a, b]; each pair is tested symmetrically (edges of a
    piercing b, then b piercing a) with the max reported.
    Returns {"a/b": count}.
    """
    report = {}
    for a, b in pairs:
        ab = group_intersections(obj, a, b)
        ba = group_intersections(obj, b, a) if ab < 50 else 0
        report["%s/%s" % (a, b)] = max(ab, ba)
    return report


# ------------------------------------------------------------ text views


def _view_char_map(obj):
    names = [mt.name for mt in getattr(obj, "bt_materials", [])]
    return {n: _PALETTE[i % len(_PALETTE)] for i, n in enumerate(sorted(names))}


def ascii_elevation(obj, view="front", width=200, height=100, chars=None):
    """Orthographic ASCII projection of a mesh, one char per matgroup.

    Raycasts one ray per cell (nearest hit wins); '.' = empty. Group
    chars are assigned by sorted group name unless `chars` overrides.
    Returns plain text (with legend) that agents can read directly.
    """
    if view not in _VIEWS:
        raise ValueError("unknown view %r (have: %s)" % (view, sorted(_VIEWS)))
    direction, u_axis, v_axis = _VIEWS[view]
    chars = chars or _view_char_map(obj)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.index_update()
    layer = bm.faces.layers.int.get(MATGROUP_LAYER)
    names = [mt.name for mt in getattr(obj, "bt_materials", [])]
    try:
        verts = [v.co.copy() for v in bm.verts]
        polys = [[v.index for v in f.verts] for f in bm.faces]
        labels = [
            (names[f[layer]] if layer and 0 <= f[layer] < len(names) else "?")
            for f in bm.faces
        ]
    finally:
        bm.free()
    if not polys:
        return "(empty mesh)"

    tree = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
    (x0, x1), (y0, y1), (z0, z1) = _bbox(verts)
    center = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    # actual u/v extents from the bbox corners
    corners = [
        Vector((cx, cy, cz)) for cx in (x0, x1) for cy in (y0, y1) for cz in (z0, z1)
    ]
    us = [c.dot(u_axis) for c in corners]
    vs = [c.dot(v_axis) for c in corners]
    u_lo, u_hi = min(us) - 0.02, max(us) + 0.02
    v_lo, v_hi = min(vs) - 0.02, max(vs) + 0.02
    far = ((x1 - x0) + (y1 - y0) + (z1 - z0) + 10.0) * 2.0

    rows = []
    for j in range(height - 1, -1, -1):
        vv = v_lo + (v_hi - v_lo) * j / max(1, height - 1)
        row = []
        for i in range(width):
            uu = u_lo + (u_hi - u_lo) * i / max(1, width - 1)
            origin = (
                center
                - direction * far
                + u_axis * (uu - center.dot(u_axis))
                + v_axis * (vv - center.dot(v_axis))
            )
            loc, _, idx, _ = tree.ray_cast(origin, direction)
            row.append(chars.get(labels[idx], "?") if loc is not None else ".")
        rows.append("".join(row))

    legend = " ".join(
        "%s=%s" % (c, n) for n, c in sorted(chars.items(), key=lambda kv: kv[1])
    )
    meta = "view=%s grid=%dx%d bbox=(%.1f..%.1f, %.1f..%.1f, %.1f..%.1f)" % (
        view,
        width,
        height,
        x0,
        x1,
        y0,
        y1,
        z0,
        z1,
    )
    return "\n".join(rows) + "\n" + meta + "\n" + legend


# ------------------------------------------------------------- aggregation


def measure_object(obj, context=None):
    """Semantic measurements for checks and regression reports."""
    context = context or {}
    report = {
        "object": obj.name,
        "counts": matgroup_counts(obj),
        "storeys": storey_bands(obj),
    }
    for group in ("window", "balcony", "railing_rails", "door"):
        bays = elevation_bays(obj, group, view="front")
        if bays:
            report["bays_front_%s" % group] = bays
    protr = group_protrusions(obj, "frame")
    if protr:
        report["frame_protrusions"] = protr
    outsets = border_outsets(obj, "roof")
    if outsets:
        report["roof_outsets"] = outsets
    return report

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

# offset direction for inside-volume parity casts (skews to miss edges)
_PARITY_DIR = Vector((0.4121, 0.5732, 0.7078)).normalized()


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
    """Per-side extents of a group's bbox beyond the walls' bbox (plan)."""
    bm, groups = _load(obj)
    try:
        wverts = [v for f in groups.get("walls", []) for v in f.verts]
        gverts = [v for f in groups.get(group, []) for v in f.verts]
        if not wverts or not gverts:
            return {}
        (wx0, wx1), (wy0, wy1), _ = _bbox(wverts)
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


def _parity_walk(tree, origin, direction=None, limit=512):
    """Number of ray crossings from origin along direction (closed mesh)."""
    direction = direction or _PARITY_DIR
    origin = origin + direction * 1e-6
    hits = 0
    for _ in range(limit):
        loc, _, _, _ = tree.ray_cast(origin, direction)
        if loc is None:
            return hits
        hits += 1
        origin = loc + direction * 1e-5
    return hits


def _sample_points(bm_faces, max_points=1500):
    """Centroid + edge midpoints of faces, capped by even stride.

    The cap bounds parity-cast runtime on dense groups (railing posts on
    big presets) while staying deterministic.
    """
    pts = []
    for f in bm_faces:
        pts.append(f.calc_center_median())
        for e in f.edges:
            pts.append((e.verts[0].co + e.verts[1].co) / 2)
    if len(pts) > max_points:
        stride = len(pts) / max_points
        pts = [pts[int(i * stride)] for i in range(max_points)]
    return pts


def interior_points(obj, inner, outer):
    """Count of `inner` group sample points strictly inside the `outer`
    group's closed volume (odd ray parity).

    Positive counts mean the two groups interpenetrate: e.g. a window
    sill buried inside a balcony platform. Touching-only geometry
    contributes only boundary-coincident points, which parity casts
    (offset from surfaces) usually miss.
    """
    verts, polys = _group_tree_polygons(obj, outer)
    if not polys:
        return 0
    tree = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)

    bm, groups = _load(obj)
    try:
        pts = _sample_points(groups.get(inner, []))
    finally:
        bm.free()

    inside = 0
    for p in pts:
        if _parity_walk(tree, p) % 2 == 1:
            inside += 1
    return inside


def intersection_report(obj, pairs):
    """Interpenetration counts for matgroup pairs.

    pairs: list of [inner, outer] (both directions reported).
    Returns {"inner/outer": count}.
    """
    report = {}
    for a, b in pairs:
        report["%s/%s" % (a, b)] = interior_points(obj, a, b)
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

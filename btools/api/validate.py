"""Structured validation helpers for mesh objects produced by the api.

All functions return JSON-serializable dicts so agents and batch tooling can
branch on the results without parsing prose.
"""

from collections import Counter

import bmesh

MATGROUP_LAYER = ".bt_material_group_index"


def _edit_or_object_bmesh(obj):
    """bmesh for obj; live edit bmesh when in edit mode, else a temporary one."""
    if obj.mode == "EDIT":
        return bmesh.from_edit_mesh(obj.data), True
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm, False


def _matgroup_names(obj):
    """Matgroup item names; [] when the addon's Object properties are not
    registered (e.g. bare headless import)."""
    mats = getattr(obj, "bt_materials", None)
    return [mt.name for mt in mats] if mats is not None else []


def matgroup_counts(obj):
    """{matgroup_name: face_count} for an object; -1 = untagged (excluded),
    out-of-range indices are reported as 'invalid_<n>' (corrupted matgroups)."""
    attr = obj.data.attributes.get(MATGROUP_LAYER)
    if attr is None:
        return {}
    total = len(obj.data.polygons)
    if total == 0:
        return {}
    names = _matgroup_names(obj)
    vals = [0] * total
    attr.data.foreach_get("value", vals)
    counts = Counter(v for v in vals if v >= 0)
    return {
        (names[i] if 0 <= i < len(names) else "invalid_%d" % i): n
        for i, n in sorted(counts.items())
    }


def matgroup_report(obj):
    """Face tagging completeness for the btools material-group system.
    Faces carrying -1 (the layer sentinel written by
    verify_matgroup_attribute_for_object) count as untagged; objects without
    the layer at all (e.g. a fresh floorplan) are treated as fully tagged."""
    names = _matgroup_names(obj)
    attr = obj.data.attributes.get(MATGROUP_LAYER)
    if attr is None:
        return {
            "groups": {},
            "num_groups": len(names),
            "untagged_faces": 0,
            "invalid_index_faces": 0,
            "all_tagged": True,
            "no_layer": True,
        }
    total = len(obj.data.polygons)
    vals = [0] * total
    if total:
        attr.data.foreach_get("value", vals)
    invalid = sum(1 for v in vals if v >= len(names))
    untagged = sum(1 for v in vals if v < 0)
    counts = matgroup_counts(obj)
    return {
        "groups": counts,
        "num_groups": len(names),
        "untagged_faces": untagged,
        "invalid_index_faces": invalid,
        "all_tagged": untagged == 0 and invalid == 0,
    }


def geometry_report(obj):
    """Common geometry problems. 'non_manifold_edges' counts edges shared by
    more than two faces (true T-junctions); boundary edges (one face) are
    legal open geometry."""
    bm, owns = _edit_or_object_bmesh(obj)
    try:
        non_manifold = [e for e in bm.edges if len(e.link_faces) > 2]
        loose_verts = [v for v in bm.verts if not v.link_edges]
        loose_edges = [e for e in bm.edges if not e.link_faces]
        zero_area = [f for f in bm.faces if f.calc_area() < 1e-9]
        return {
            "non_manifold_edges": len(non_manifold),
            "loose_verts": len(loose_verts),
            "loose_edges": len(loose_edges),
            "zero_area_faces": len(zero_area),
            "counts": {
                "verts": len(bm.verts),
                "edges": len(bm.edges),
                "faces": len(bm.faces),
            },
            "clean": not (non_manifold or loose_verts or loose_edges or zero_area),
        }
    finally:
        if not owns:
            bm.free()


def normal_report(obj):
    """Face-orientation consistency: counts 'flip seams' -- mesh edges shared
    by two faces whose normals point in opposing directions. Non-zero values
    indicate inverted patches (see issues #229/#204)."""
    bm, owns = _edit_or_object_bmesh(obj)
    try:
        seams = 0
        for e in bm.edges:
            if len(e.link_faces) == 2:
                if e.link_faces[0].normal.dot(e.link_faces[1].normal) < -0.9:
                    seams += 1
        return {"flip_seams": seams, "consistent": seams == 0}
    finally:
        if not owns:
            bm.free()


def validate_object(obj, expect=None, include_geometry=True):
    """Full validation report for a mesh object.

    expect: optional dict of assertions:
        {"groups": ["walls", "roof"]}  -- matgroups that must exist and have faces
    include_geometry: when False, geometry problems are reported but do not
        affect `ok` (matgroup completeness is the addon's core contract;
        geometry seams are advisory).
    Returns {"ok": bool, ...} with all sub-reports embedded.
    """
    expect = expect or {}
    mat = matgroup_report(obj)
    geo = geometry_report(obj)
    nor = normal_report(obj)

    problems = []
    if not mat["all_tagged"]:
        problems.append(
            "%d untagged/invalid faces"
            % (mat["untagged_faces"] + mat["invalid_index_faces"])
        )
    if include_geometry and not geo["clean"]:
        problems.append(
            "geometry issues: %s"
            % {
                k: geo[k]
                for k in (
                    "non_manifold_edges",
                    "loose_verts",
                    "loose_edges",
                    "zero_area_faces",
                )
                if geo[k]
            }
        )

    missing_groups = []
    for name in expect.get("groups", []):
        if mat["groups"].get(name, 0) == 0:
            missing_groups.append(name)
    if missing_groups:
        problems.append("missing/empty matgroups: %s" % missing_groups)

    return {
        "ok": not problems,
        "object": obj.name,
        "problems": problems,
        "matgroups": mat,
        "geometry": geo,
        "normals": nor,
    }

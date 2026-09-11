"""Declarative geometry expectations for presets and built objects.

Checks are machine-verifiable contracts about *spatial* correctness --
alignment, interpenetration, counts per storey -- as opposed to
validate_object's tagging contract. They run on measurements from
btools.api.probe, so failures come with numbers, not pixels.

Each check is a dict; common keys:
    kind    -- check type (see CHECK_KINDS)
    xfail   -- true for known defects: reported, never fails the run
    reason  -- why an xfail exists (required when xfail)

run_checks(...) returns {"ok": bool, "failures": [...], "results": [...]}
with every result carrying the measured values.
"""

from . import probe
from .validate import matgroup_counts

CHECK_KINDS = (
    "group_present",
    "no_intersection",
    "count_per_storey",
    "bay_alignment",
    "protrusion_range",
    "symmetric_outset",
)


def _result(check, ok, detail):
    res = {"kind": check["kind"], "ok": bool(ok), "detail": detail}
    if check.get("xfail"):
        res.update({"xfail": True, "reason": check.get("reason", "")})
    return res


def _check_group_present(obj, check):
    counts = matgroup_counts(obj)
    missing = [g for g in check["groups"] if counts.get(g, 0) == 0]
    return not missing, {
        "missing": missing,
        "counts": {g: counts.get(g, 0) for g in check["groups"]},
    }


def _check_no_intersection(obj, check):
    max_inside = check.get("max_inside", 0)
    report = probe.intersection_report(obj, [tuple(p) for p in check["pairs"]])
    bad = {k: v for k, v in report.items() if v > max_inside}
    return not bad, {"pairs": report, "threshold": max_inside}


def _check_count_per_storey(obj, check):
    group = check["group"]
    min_each = check.get("min_each", 1)
    max_each = check.get("max_each")
    skip_storeys = check.get("skip_storeys", 0)
    bands = probe.storey_bands(obj)
    counts = probe.counts_per_storey(obj, group, bands)
    expected = check.get("storeys")
    target = {}
    if expected is not None:
        target = {
            "storey_%d" % i: counts.get("storey_%d" % i, 0)
            for i in range(skip_storeys, skip_storeys + expected)
        }
        bad = {b: n for b, n in target.items() if n < min_each}
        if max_each is not None:
            bad.update({b: n for b, n in target.items() if n > max_each})
        return not bad, {
            "per_storey": counts,
            "violations": bad,
            "expected_bands": sorted(target),
        }
    bad = {}
    for band, n in counts.items():
        if n < min_each or (max_each is not None and n > max_each):
            bad[band] = n
    return not bad, {"per_storey": counts, "violations": bad}


def _check_bay_alignment(obj, check):
    view = check.get("view", "front")
    tol = check.get("tol", 0.1)
    a = probe.elevation_bays(obj, check["a"], view=view, tol=check.get("tol_a", 0.2))
    b = probe.elevation_bays(obj, check["b"], view=view, tol=check.get("tol_b", 0.35))
    if not a:
        return False, {"error": "no %s bays in %s view" % (check["a"], view)}
    if not b:
        return False, {
            "error": "no %s bays in %s view (feature missing?)" % (check["b"], view)
        }
    # containment: every a-bay center must be covered by some b-bay span
    uncovered = []
    for bay in a:
        c = bay["center"]
        if not any(bb["min"] - tol <= c <= bb["max"] + tol for bb in b):
            uncovered.append(round(c, 3))
    return not uncovered, {
        "a_centers": [round(x["center"], 3) for x in a],
        "b_spans": [[round(x["min"], 3), round(x["max"], 3)] for x in b],
        "tol": tol,
        "uncovered_a_centers": uncovered,
    }


def _check_protrusion_range(obj, check):
    lo, hi = check["min"], check["max"]
    planes = probe.group_protrusions(obj, check.get("group", "frame"))
    relevant = [p for p in planes if p["normal"][2] == 0]  # wall-side planes only
    if not relevant:
        return False, {"error": "no vertical wall planes found"}
    protrusions = [p["protrusion"] for p in relevant]
    ok = all(lo <= v <= hi for v in protrusions)
    return ok, {
        "per_plane": [{"d": p["d"], "protrusion": p["protrusion"]} for p in relevant],
        "range": [min(protrusions), max(protrusions)],
    }


def _check_symmetric_outset(obj, check):
    tol = check.get("tol", 0.02)
    outsets = probe.border_outsets(obj, check.get("group", "roof"))
    if not outsets:
        return False, {"error": "empty outset report"}
    vals = [v for v in outsets.values()]
    spread = max(vals) - min(vals)
    return spread <= tol, {"outsets": outsets, "spread": round(spread, 4), "tol": tol}


_RUNNERS = {
    "group_present": _check_group_present,
    "no_intersection": _check_no_intersection,
    "count_per_storey": _check_count_per_storey,
    "bay_alignment": _check_bay_alignment,
    "protrusion_range": _check_protrusion_range,
    "symmetric_outset": _check_symmetric_outset,
}


def run_checks(obj, checks, context=None):
    """Run declarative checks against a built object.

    context is reserved for preset metadata (floor heights etc.); probes
    currently derive storeys from geometry. Returns
    {"ok", "failures", "results"}; xfail checks never affect ok.
    """
    results = []
    for check in checks:
        kind = check.get("kind")
        runner = _RUNNERS.get(kind)
        if runner is None:
            res = {
                "kind": str(kind),
                "ok": False,
                "detail": {"error": "unknown kind (have: %s)" % sorted(CHECK_KINDS)},
            }
        else:
            try:
                ok, detail = runner(obj, check)
                res = _result(check, ok, detail)
            except Exception as exc:  # probe failure = failing check
                res = _result(
                    check, False, {"error": "%s: %s" % (type(exc).__name__, exc)}
                )
        results.append(res)

    failures = [r for r in results if not r["ok"] and not r.get("xfail")]
    return {"ok": not failures, "failures": failures, "results": results}

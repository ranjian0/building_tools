"""Bay-grid facade layer -- a CGA subset over the existing feature api.

Bay grids are horizontal subdivisions of a selector face. Each bay maps
to a feature placement through ``size_offset``: sizes and offsets are
absolute meters in the FACE-LOCAL frame (x runs left-to-right along the
wall, y up; offset is measured from the face center -- see
``SizeOffsetProperty`` and ``create_window_split``), so no world-space
math is needed and the layout follows the face regardless of rotation.

Rules sharing an ``align`` key derive the same grid per face: the first
rule to touch a face establishes the grid, later rules reuse it. This
keeps multi-rule facades (windows + balconies, shutters over windows)
aligned under floorplan scaling -- the hand-tuned ``array.count``
coupling it replaces breaks there.

Wall faces persist across feature applications (features extrude from
sub-faces without consuming the parent), so face indices and widths are
stable between rules and the align cache stays valid.
"""

from dataclasses import dataclass

from .core import OPTION_TYPES, FaceTarget, apply_feature, options_from_dict
from .select import select

__all__ = ["BayGrid", "bay_matches", "face_widths", "resolve_bay_grid"]


@dataclass
class BayGrid:
    """Horizontal bay layout for one face."""

    count: int
    face_width: float
    bay_width: float

    def center_offset(self, index):
        """Face-local x offset of a bay's center (from the face center)."""
        return -self.face_width / 2 + (index + 0.5) * self.bay_width

    def clamp_size(self, size):
        """Clamp a (width, height) rule size to fit inside a bay."""
        return (min(size[0], self.bay_width), size[1])


def resolve_bay_grid(face_width, bays, bay_width):
    """Bay grid for a face.

    bays      -- int count, or "fill" (as many bays as fit)
    bay_width -- required for "fill"; bays stretch to cover the face
                 evenly (CGA float/repeat-split semantics), so the grid
                 stays symmetric with no remainder strip.
    """
    if bays == "fill":
        if not bay_width or bay_width <= 0.0:
            raise ValueError('bays="fill" requires a positive bay_width')
        count = max(1, int(face_width // bay_width))
    else:
        count = max(1, int(bays))
    return BayGrid(count, face_width, face_width / count)


def bay_matches(index, count, where):
    """Evaluate a rule's ``where`` conditions for bay ``index``.

    Recognized keys (unknown keys are ignored for forward compat):
      bay_index -- "even" | "odd" | "first" | "last" | int | list[int]
    """
    if not where:
        return True
    for key, value in where.items():
        if key != "bay_index":
            continue
        if value == "even" and index % 2 != 0:
            return False
        if value == "odd" and index % 2 != 1:
            return False
        if value == "first" and index != 0:
            return False
        if value == "last" and index != count - 1:
            return False
        if isinstance(value, int) and index != value:
            return False
        if isinstance(value, (list, tuple)) and index not in value:
            return False
    return True


def face_widths(obj, indices):
    """{face_index: width} for the given faces (temp bmesh, no edits)."""
    import bmesh

    from ..utils import calc_face_dimensions

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()  # fresh bmeshes have unset (0) indices
    try:
        return {i: calc_face_dimensions(bm.faces[i])[0] for i in indices}
    finally:
        bm.free()


def _face_anchors(obj, indices):
    """Pre-edit geometry anchors for per-bay placement: center, face-local
    x direction and normal per face index (temp bmesh, no edits)."""
    import bmesh

    from ..utils import local_xyz

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    try:
        anchors = []
        for i in indices:
            f = bm.faces[i]
            x, _y, _z = local_xyz(f)
            anchors.append(
                {
                    "center": f.calc_center_median().copy(),
                    "x_dir": x.normalized(),
                    "normal": f.normal.copy(),
                }
            )
        return anchors
    finally:
        bm.free()


def locate_wall_fragment(obj, target, normal, tol=0.05):
    """Face index of the wall fragment containing ``target`` on the plane
    defined by ``normal`` (per-bay placement after earlier bays split the
    original face; indices do not survive edits). Largest match wins."""
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    try:
        best, best_area = None, -1.0
        for f in bm.faces:
            n = f.normal
            if (
                abs(n.x - normal.x) > 0.1
                or abs(n.y - normal.y) > 0.1
                or abs(n.z - normal.z) > 0.1
            ):
                continue
            c = f.calc_center_median()
            # -- containment within the face's plane bounds
            dims = [v.co for v in f.verts]
            xs = [v.x for v in dims]
            ys = [v.y for v in dims]
            zs = [v.z for v in dims]
            if not (
                min(xs) - tol <= target.x <= max(xs) + tol
                and min(ys) - tol <= target.y <= max(ys) + tol
                and min(zs) - tol <= target.z <= max(zs) + tol
            ):
                continue
            # -- target must lie on the fragment's plane
            if abs((target - c).dot(n)) > 0.05:
                continue
            area = f.calc_area()
            if area > best_area:
                best, best_area = f.index, area
        return best
    finally:
        bm.free()


def apply_facade_rules(
    obj,
    rules,
    floor_count,
    floor_height,
    rng=None,
    record=None,
):
    """Apply facade rules to `obj` (the bay-grid facade layer).

    Shared by build_preset and RuleContext.facade. Returns
    (summaries, failed_result_or_None): `summaries` carries one entry per
    rule application or skip; `failed_result` is set when a rule
    application errored (caller decides whether to abort)."""
    summaries = []

    def _skip(feature, why):
        summaries.append(
            {
                "feature": feature,
                "status": "skipped",
                "matgroup_counts": {},
                "errors": [],
                "warnings": [why],
            }
        )

    # -- bay-grid cache: wall faces persist across feature
    #    applications (features extrude from sub-faces), so face
    #    indices are stable between rules
    align_grids = {}
    for rule_idx, rule in enumerate(rules):
        storeys = rule.storeys if rule.storeys else tuple(range(floor_count))
        faces = select(
            obj,
            rule.faces,
            floor_height=floor_height,
            storeys=storeys,
            group="walls",
        )
        if not faces:
            summaries.append(
                {
                    "feature": rule.feature,
                    "status": "skipped",
                    "matgroup_counts": {},
                    "errors": [],
                    "warnings": ["no faces matched %r" % rule.faces],
                }
            )
            continue

        per_placement = (
            rule.has_grid or rule.where or (rng is not None and rule.variations)
        )
        if not per_placement:
            options = options_from_dict(OPTION_TYPES[rule.feature], dict(rule.options))
            res = apply_feature(rule.feature, options, FaceTarget(obj, faces))
            record(rule.feature, res)
            if not res.ok:
                return res
            continue

        widths = face_widths(obj, faces)
        for face_pos, face_idx in enumerate(faces):
            grid = None
            if rule.align is not None:
                grid = align_grids.get((rule.align, face_idx))
            if grid is None and rule.bays != 1:
                grid = resolve_bay_grid(widths[face_idx], rule.bays, rule.bay_width)
                if rule.align is not None:
                    align_grids[(rule.align, face_idx)] = grid

            if (
                grid is not None
                and grid.count > 1
                and not (rule.where or (rng is not None and rule.variations))
            ):
                # -- uniform grid: the array mechanism IS the bay grid
                #    (count elements at even subdivisions, one edit
                #    session, battle-tested placement)
                rule_options = dict(rule.options)
                so = dict(rule_options.get("size_offset") or {})
                size = so.get("size")
                if size is not None:
                    so["size"] = grid.clamp_size(size)
                    rule_options["size_offset"] = so
                arr = dict(rule_options.get("array") or {})
                arr["count"] = grid.count
                rule_options["array"] = arr
                options = options_from_dict(OPTION_TYPES[rule.feature], rule_options)
                res = apply_feature(rule.feature, options, FaceTarget(obj, [face_idx]))
                summaries.append(
                    {
                        "feature": rule.feature,
                        "status": res.status,
                        "matgroup_counts": res.matgroup_counts,
                        "errors": res.errors[:1],
                    }
                )
                if record is not None:
                    record(rule.feature, res)
                if not res.ok:
                    return res
                continue

            # -- per-bay path (where / variations): apply one bay at a
            #    time, re-locating the target wall fragment after each
            #    split (face indices do not survive edits)
            anchors = _face_anchors(obj, [face_idx])
            placements = range(grid.count) if grid is not None else (None,)
            for bay in placements:
                if bay is not None and not bay_matches(bay, grid.count, rule.where):
                    continue

                rule_options = dict(rule.options)
                if bay is not None and grid.count > 1:
                    # -- position within the bay: centered, rule
                    #    offset.x nudges within it; size clamped
                    so = dict(rule_options.get("size_offset") or {})
                    size = so.get("size")
                    if size is not None:
                        so["size"] = grid.clamp_size(size)
                    offset = list(so.get("offset") or (0.0, 0.0))
                    offset[0] += grid.center_offset(bay)
                    so["offset"] = offset
                    rule_options["size_offset"] = so

                if rng is not None and rule.variations:
                    path = ("facade", rule.feature, rule_idx, face_pos)
                    if bay is not None:
                        path += (bay,)
                    for opt_name, pool in rule.variations.items():
                        rule_options[opt_name] = rng.choice(path + (opt_name,), pool)

                options = options_from_dict(OPTION_TYPES[rule.feature], rule_options)
                if bay is None or grid is None or grid.count == 1:
                    target_idx = face_idx
                else:
                    anchor = anchors[0]
                    target_world = anchor["center"] + anchor["x_dir"] * (
                        grid.center_offset(bay)
                    )
                    target_idx = locate_wall_fragment(
                        obj, target_world, anchor["normal"]
                    )
                    if target_idx is None:
                        summaries.append(
                            {
                                "feature": rule.feature,
                                "status": "skipped",
                                "matgroup_counts": {},
                                "errors": [],
                                "warnings": [
                                    "bay %d: no wall fragment at target" % bay
                                ],
                            }
                        )
                        continue
                res = apply_feature(
                    rule.feature, options, FaceTarget(obj, [target_idx])
                )
                summaries.append(
                    {
                        "feature": rule.feature,
                        "status": res.status,
                        "matgroup_counts": res.matgroup_counts,
                        "errors": res.errors[:1],
                    }
                )
                if record is not None:
                    record(rule.feature, res)
                if not res.ok:
                    return res

    return summaries, None

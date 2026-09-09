# Plan: Balconies create inverted face normals (#229)

- **Issue**: https://github.com/ranjian0/building_tools/issues/229
- **Type**: Bug
- **Symptom**: Some faces of newly created balconies have flipped normals
  (visible with viewport Face Orientation overlay); fixable manually with
  Shift+Ctrl+N.

## Problem

Balcony geometry is built with a chain of extrude/inset/dissolve bmesh ops.
Some of these (`inset_region` with `use_boundary`, `dissolve_faces`,
`delete(..., context="FACES_ONLY")`) can leave faces whose winding no longer
matches the wall's outward orientation. There is no final normal-consistency
pass scoped to the new balcony geometry.

## Current Code State

- `btools/building/balcony/balcony_types.py:53-69` `create_balcony_ungrouped` —
  per face: split → `extrude_balcony` (extrude + translate along `face.normal`)
  → railing → `delete(geom=[f], context="FACES_ONLY")`. Deleting only faces
  leaves edge/vert winding from the original face on the inner lip.
- `btools/building/balcony/balcony_types.py:83-107` `extrude_balcony_grouped` —
  repeated `inset_region(use_boundary=True)` + `dissolve_degenerate`; faces added
  back are filtered **by normal tuple match** (line 105) — normals here are only
  trustworthy if nothing flipped earlier in the chain.
- `btools/building/balcony/balcony_types.py:34-51` `create_balcony_grouped` —
  `dissolve_faces(...)["region"]` for the railing base can merge faces with
  inconsistent winding.
- `btools/building/balcony/balcony_ops.py:38+` `build` — no recalc of normals at
  the end. (Roof code does the opposite: `extrude_and_outset` calls
  `bmesh.ops.recalc_face_normals` at `roof_types.py:439`.)

Note: `bmesh.ops.recalc_face_normals` makes normals **consistent/outward per
island**, which is what we want for a closed balcony slab, but the balcony is
welded into the wall mesh — so recalc must be scoped to the new faces plus their
adjacent wall faces, not `bm.faces`.

## Implementation Steps

1. Track all faces created during balcony generation:
   - Thread a `new_faces` set through `create_balcony_*`, `extrude_balcony*`,
     and railing helpers (each op returns `geom` / face maps that can be
     diffed), or simpler: snapshot `set(bm.faces)` before and diff after
     `create_balcony` in `balcony_ops.build`.
2. After generation completes (in `build`, `balcony_ops.py`), run a **scoped**
   normal repair:
   - `bmesh.ops.recalc_face_normals(bm, faces=orig_faces_around_boundary | new_faces)`
     where `orig_faces_around_boundary` = faces sharing an edge with new faces.
     This keeps the wall's existing orientation authoritative at the seam
     (recalc propagates from existing consistent faces into the new island).
3. For the **grouped** path, additionally verify inset-result normal filtering
   (line 105) uses the *post-recalc* normals; move the filter after step 2 or
   compare against the source face's stored normal rather than `.to_tuple(3)` equality.
4. Also apply the same scoped recalc to **stairs** and **fill** builds if quick
   checks show flipped faces there (same op chain); keep scope minimal per the issue.

## Acceptance Criteria

- Balcony (grouped + ungrouped, with/without railing) on flat and curved walls
  shows **zero red (inside-out) faces** in Face Orientation overlay.
- Wall faces keep their pre-existing orientation (no flips introduced on the wall).

## Test Plan

- Headless test: create wall + balcony; for every new face, assert its normal
  points away from the wall interior (dot with outward radial vector > 0 for
  curved wall case; dot with wall normal > 0 for the front faces).

## Risks

- Over-aggressive recalc could flip user-authored inverted-wall scenes (see
  plan 204); scoping to new faces + boundary neighbors avoids this.

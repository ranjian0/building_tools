# Plan: Depth issues on inverted walls (#204)

- **Issue**: https://github.com/ranjian0/building_tools/issues/204
- **Type**: Bug
- **Symptom**: After the user flips wall normals (Mesh » Normals » Flip) to
  build inward-facing structures, doors/windows extrude in inconsistent
  directions; balconies land on the wrong side; multiple selections on the
  interior behave differently than incremental selections.

## Problem

All arch-type elements (door/window/multigroup/fill) determine "outward" from
`face.normal` at generation time. The addon implicitly assumes floorplan normals
point **outward**. When users invert walls, `face.normal` now points to the
building interior, and:

- depth/frame extrusion follows the flipped normal into the wall,
- `size_offset.offset` axes flip handedness,
- balcony/railing "front" detection (`get_top_faces`, `sort_edges` with normal)
  picks the wrong side.

There is no global notion of "which side is outside", so any per-operator
heuristic is inherently ambiguous on flipped meshes.

## Current Code State

- `btools/building/door/door_ops.py:63-69` `validate_door_faces` filters by
  `normal.z == 0` and rectangularity only — no orientation handling.
- `btools/building/arch.py:79+` `fill_arch` / `create_arch` extrude along
  face normal / frame depth direction derived from selection.
- `btools/utils/util_mesh.py` helpers used across types accept `normal` args
  from `local_xyz(face)` — all downstream of the face's own normal.
- Balcony: `balcony_types.py:53-69` — extrudes along `face.normal` (same issue
  as reported for balconies in the thread).
- No documentation states the outward-normal requirement (wiki/README silent).

## Implementation Steps

1. **Define the convention explicitly**: walls must have outward-facing normals
   for correct results. Document this in README/wiki and in operator tooltips.
2. **Detection + warning**: in `build()` for door/window/multigroup/balcony,
   if the object contains a floorplan-like mesh, estimate the building interior
   (median of all verts, or ray-casting parity from the face median along its
   normal) and detect faces whose normal points *toward* the interior centroid
   for a majority of the selection. Show a `popup_message` warning
   ("Selection normals appear inverted — recalculate outside?") with a button to
   run `bmesh.ops.recalc_face_normals` on the object (matching #229's repair
   utility).
3. **Don't auto-flip silently**: recalc on the whole mesh would fight users who
   intentionally model inside-out (this very issue). Keep it an explicit,
   confirmable repair action, exposed once per object via a small
   `BTOOLS_OT_fix_normals` operator in the Material/Building Tools panel.
4. **Make depth direction configurable where cheap**: for arch elements, the
   direction of `add_arch_depth` could take a `flip` bool derived from the
   detection in (2) so *individual* selections on inverted meshes still work:
   if the face normal points toward interior, invert depth sign.
   Apply the same sign logic to balcony extrusion normal.
5. Ensure the multi-select inconsistency reported (CTRL-select in two batches
   vs one) is resolved by (4): behavior becomes a pure function of each face's
   normal, not of selection batching.

## Acceptance Criteria

- On a mesh with intentionally flipped normals, doors/windows/balconies extrude
  to the side the user intends once the per-face sign logic applies; warning
  popup offers the one-click repair.
- On standard meshes, behavior is unchanged.

## Test Plan

- Headless test: wall cube with flipped normals; run door build; assert frame
  geometry lies on the expected side per the flip rule.

## Risks

- Interior-centroid heuristic fails on concave/courtyard plans (relates to
  #103). Use ray-parity instead of centroid when the plan is concave; keep the
  heuristic advisory-only (warning, never auto-modify).

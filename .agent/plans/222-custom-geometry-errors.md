# Plan: Fix custom geometry placement errors (#222)

- **Issue**: https://github.com/ranjian0/building_tools/issues/222
- **Type**: Bug
- **Symptom**: A ring mesh placed as custom geometry becomes deformed and/or
  offset on the wall; placement sometimes fails entirely.

## Problem

`BTOOLS_OT_add_custom` copies the user object's mesh into the wall bmesh and
then transforms it onto the selected face. Several assumptions break for
non-convex / radially-symmetric objects (rings, cylinders) and for objects whose
"front" isn't aligned with the wall's local axes.

## Current Code State

- `btools/building/customobj.py:117-141` `place_custom_object` — subdivides the
  wall face, then calls `place_object_on_face` per split.
- `btools/building/customobj.py:176-182` `duplicate_into_bm`:
  - Uses `bm.from_mesh(obj.data.copy())` and identifies inserted faces by
    `f.index >= max_index`. **`f.index` is only valid after `bm.faces.ensure_lookup_table()`
    and index-based detection is fragile** if any earlier operator reordered/added faces.
  - `from_mesh` drops per-object transforms (handled by `apply_transforms`) but
    also ignores custom split normals / sharp edges — a ring with smooth shading
    can come in with recomputed normals.
- `btools/building/customobj.py:216-225` — bounds computed as
  `current_size = [max(dims.x, dims.y), dims.z]` using **object-space world dims**.
  For a ring lying in the XY plane, `dims.z` is small and the `max(x, y)` collapses
  both wall axes to the same value → wrong scale on one axis → the reported
  "squash/deform".
- `btools/building/customobj.py:255-283` `transform_parallel_to_face`:
  - Derives the object's facing direction from "coplanar bound faces"
    (`get_coplanar_faces` uses the 4 bounding corners) — meaningless for a ring
    where corner verts link to faces on all sides; `angle_signed` can raise
    `ValueError` and silently falls back to `angle = 0` (the `TODO` at line 268).
  - Result: rotation is skipped → object placed at an arbitrary/offset orientation.
- `btools/building/customobj.py:286-301` `scale_to_size` scales along
  `local_xyz(face)` axes — correct only if the object was already rotated to face space.

## Implementation Steps

1. **Deterministic insertion**: in `duplicate_into_bm`, use
   `bm.faces.ensure_lookup_table()` immediately after `from_mesh` and collect
   faces by index range `[max_index, len(bm.faces))`; assert the count matches
   the source mesh face count; fall back to comparing verts sets if not.
2. **Track inserted geometry explicitly**: tag inserted verts with a temporary
   bmesh layer (or keep the returned vert list) instead of index arithmetic.
3. **Rework orientation**: replace the "coplanar corner faces" heuristic:
   - Require (and document) the custom object's front to be its `-Y` face, and
     use its local bounding box to find the face plane; or
   - Compute orientation from the object's **largest-area faces whose normal is
     most aligned with a single dominant axis**, which works for rings/frames.
   - Apply rotate → translate with a single matrix built from the target face's
     `local_xyz` frame instead of separate ops.
4. **Fix scaling**: compute the object's size in the **target face's local
   frame** (project bounds onto `local_xyz(face)` axes) rather than
   `max(dims.x, dims.y)`; scale per-axis; never scale Z by a collapsed axis.
5. **Preserve shading**: after `from_mesh`, carry over `smooth` flags
   (`f.smooth = src.smooth`) and sharp edges so rings don't lose flat/smooth shading.
6. Keep the existing `MaterialGroup.CUSTOM` tagging and material transfer.

## Acceptance Criteria

- Placing a torus/ring on a straight wall: correct orientation, no squash,
  offset property respected.
- Placing on a rotated/angled wall face works the same as on axis-aligned walls.
- Objects with non-uniform scale and applied transforms behave identically to
  untransformed ones.

## Test Plan

- Headless test in `tests/`: build a wall, programmatically place a ring mesh on
  a face, assert: bounding box of result matches `size_offset.size` within
  tolerance; all result verts lie within `depth` of the face plane; face count preserved.

## Risks

- Changing the expected "front" convention may alter behavior for existing
  user assets; mitigate by auto-detecting first, and only warning if ambiguous.

# Plan: Generate roofs on multiple faces at once (#187)

- **Issue**: https://github.com/ranjian0/building_tools/issues/187
- **Type**: Enhancement
- **Also requests**: raise the property limits for thickness/outset/height
  (currently clamped to 0.01–1.0 m in `roof_props.py`).

## Current State

- `btools/building/roof/roof_ops.py` `build` passes **all selected faces** to
  `create_roof`, but the skeleton types immediately collapse them:
  - `create_hip_roof` (`roof_types.py:108-136`): `extrude_and_outset` dissolves
    the extruded top faces into **one** face (`roof_types.py:424-432`) —
    disjoint selections get merged/destroyed; only the active face survives in
    practice.
  - Gable has the same behavior via `extrude_and_outset`.
  - Flat roof also collapses to one top face (usually acceptable, but
    inconsistent with expectations).
- `roof_props.py:30-70`: `thickness`/`outset` max `1.0`, `height` max `10.0`.

## Implementation Steps

1. **Per-face-group iteration**: in `create_roof` (`roof_types.py:21-31`),
   partition `faces` into connected groups
   (`bmesh` flood fill over shared edges among selected faces — add
   `get_selection_groups` reuse from `util_common.py`, already used by balcony).
2. Run the existing per-type creation once per group:
   - For HIP/GABLE, bypass the dissolve step in `extrude_and_outset` when the
     group has multiple faces *only if* they are contiguous; disjoint groups
     are handled by (1). The dissolve is what destroys disjoint inputs — gate
     it on "faces form one connected region".
3. **Undo/popup batching**: `popup_message` in `create_skeleton_faces`
   (intersection warning) would pop per group — aggregate errors and show once
   with a count.
4. **Raise property limits**: thickness/outset max → 10.0, height max → 100.0
   (`get_scaled_unit` keeps unit scaling). Soft warning (console) when outset
   exceeds inradius of the face to preempt the "Roof Intersection Detected" error.
5. Track progress for large batches (city-scale use case from the issue):
   `context.window_manager.progress_begin/update/end` around the group loop.

## Acceptance Criteria

- Selecting N disjoint faces on a floorplan object and clicking Add Roof
  creates N roofs in one operation.
- Contiguous multi-face selections behave as one roof (unchanged).
- Large outset/height values are accepted (limits raised) and produce the
  existing intersection warning rather than silent breakage.

## Test Plan

- Headless: floorplan with 3 disjoint faces (joined custom outlines) → hip
  roof → assert 3 roof face clusters, all faces tagged `ROOF`.

## Risks

- Low; mostly loop restructuring. Depends on shared refactor from
  `040-new-roof-types.md` step 1 (extract common skeleton path) to avoid
  triplicating the loop.

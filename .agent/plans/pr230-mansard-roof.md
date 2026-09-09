# Plan: Review & land PR #230 — Mansard roof type

- **PR**: https://github.com/ranjian0/building_tools/pull/230
- **Author**: sigmundfred ("Mansard type added to roof generation")
- **Type**: Feature contribution (also un-ticks the *Mansard* item of issue #40)
- **Changes**: +151 / −9 across
  `btools/building/floor/floor_types.py`, `btools/building/roof/roof_props.py`,
  `btools/building/roof/roof_types.py`

## What the PR does

- Adds `MANSARD` enum entry to `roof_types` and a `create_mansard_roof()`:
  negative inset (outset) of the base face → extrude up by
  `height * height_ratio` → scale top by `mansard_ratio` → extrude again by
  `height * (1 - height_ratio)` → scale again (a two-step curved mansard profile).
- Adds `height_ratio` and `mansard_ratio` float props + UI draw block.
- Also contains unrelated drive-by edits to `floor_types.py::create_columns`
  (comments, decoration tweaks) — which collides with plan #226.

## Review Findings (blockers before merge)

1. **Debug output left in**: `print(longest_edge)` and the per-edge length loop
   in `create_mansard_roof` — remove.
2. **Large commented-out straight-skeleton block** — remove (or re-purpose; see
   step 4 below).
3. **Property bugs**:
   - `height_ratio` / `mansard_ratio` are pure ratios but wrapped in
     `get_scaled_unit(...)` and declared `unit="LENGTH"` — wrong for a
     unitless 0–1 factor; scene unit scaling would corrupt them.
   - Both props have the same UI name "Height of curvature" — rename
     ("Lower Slope Height" / "Top Width Ratio" or similar).
   - `mansard_ratio` semantics: it's a scale factor (0.5–0.9), so name it
     accordingly.
4. **No material-group tagging**: the mansard faces never get
   `ROOF` / `ROOF_HANGS` groups (every other roof type does; `map_new_faces`
   decorator or explicit `add_faces_to_group` needed). Material Tools will show
   untagged faces — same class of bug as #228.
5. **Geometry robustness**:
   - `faces[0]` assumed to be the single base face (users can select multiple);
     guard or reuse the `extrude_and_outset` helper for consistency with other types.
   - Scaling is in world XY — rotated floorplans get sheared/skewed mansards;
     scale in the face's local frame (`local_xyz`).
   - `get_top_face` lacks trailing newline and duplicates logic from
     `extrude_and_outset`; factor the helper out and share.
6. **Style/lint**: trailing whitespace, missing EOF newline, black formatting —
   run `just format` + `just check`.
7. **Scope creep**: `floor_types.py` column changes belong to #226 work — ask
   contributor to drop them from this PR (or split into a separate PR), to keep
   the mansard diff reviewable.

## Implementation Steps (to finish the feature)

1. Apply fixes 1–3, 6, 7 above.
2. Tag faces: lower steep slope faces → `ROOF_HANGS`, top shallow faces →
   `ROOF` (consistent with hip/gable).
3. Local-frame scaling; support multi-face selection by iterating the same way
   `create_flat_roof` does (ties into plan #187).
4. Optionally: make the two-step profile N-step (`profile_segments` int) so the
   "curved" mansard can be approximated better later — can be a follow-up.
5. Add headless test: box floorplan → mansard roof → assert top face area ≈
   `mansard_ratio²` × base area; all faces tagged; FINISHED status.
6. Update `README`/wiki roof docs + #40 checklist (tick Mansard).

## Acceptance Criteria

- Mansard roof renders correctly on rectangular and L-shaped floorplans, with
  material groups assigned and no console output.
- mypy/black clean; tests pass (`just test`).

## Risks

- Low once cleanup lands; main coordination risk is the `floor_types.py`
  overlap with #226 work.

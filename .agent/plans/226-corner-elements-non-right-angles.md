# Plan: Corner elements (columns, posts) only work for 90° (#226)

- **Issue**: https://github.com/ranjian0/building_tools/issues/226
- **Type**: Bug (labeled **High Priority**)
- **Symptom**: Adding columns to a circular floorplan raises an error; balcony
  corner posts on circular walls render misaligned/broken. Any corner that isn't
  a right angle misbehaves.

## Problem

Corner-dependent features assume axis-aligned, right-angle corners:

- **Columns** (`btools/building/floor/floor_types.py:142+` `create_columns`):
  iterates `face.verts`, computes `dir_vector = v.co - center`, and builds the
  column frame from the two edges at each vertex assuming perpendicularity.
  On a circular floorplan every vertex is a near-180° "corner" and the
  frame construction degenerates (error reported in screenshot).
- **Railing corner posts** (`btools/building/railing/railing.py`): posts are
  placed at rail segment joints with orientation from perpendicular offsets —
  fine at 90°, wrong at obtuse/reflex angles (visible misplacement on curved walls).
- **Balcony posts** reuse the railing module, inheriting the same limitation.

The issue itself notes: "there will be more areas where the add-on only works
for 90-degree corners" — so the fix should introduce a shared corner/angle
utility, not a local patch.

## Current Code State

- `btools/building/floor/floor_types.py:142-220` — `create_columns` (also the
  file touched by PR #230, see plan `pr230-mansard-roof.md`; coordinate both).
  Uses `is_parallel`, `vec_equal` helpers — exact-equality checks that fail on
  non-axis-aligned vectors.
- `btools/building/railing/railing.py` — `create_railing(bm, faces, prop, normal)`;
  rail fills (`btools/building/railing/railing_props.py` `RailFillProperty`:
  POSTS/WALL/RAILS) build from face edges with axis-assumed offsets.
- `btools/utils/util_mesh.py` — no generic "corner angle at vert" / "bisector
  frame" helper exists yet.

## Implementation Steps

1. **Add corner utilities** to `btools/utils/util_mesh.py`:
   - `corner_angle(vert, face)` — interior angle via loop tangent vectors.
   - `corner_frame(vert, face)` — returns (inward bisector, tangent) basis for
     placing objects at arbitrary-angle corners.
   - Tolerance-based `is_parallel`/`vec_equal` replacements
     (`is_parallel(a, b, eps=1e-4)`).
2. **Columns**: rework `create_columns` to:
   - Filter candidate corners by `corner_angle` within `[min_angle, max_angle]`
     props (skip near-180° verts on circles unless `corner_degrees` tolerance says otherwise).
   - Build each column from `corner_frame` (rotated cube), so depth/width follow
     the wall direction and the bisector; decoration extrudes stay local-frame based.
3. **Railing posts**: place posts at rail joints using the bisector frame;
   post cross-section rotated to bisect the turn angle; for near-straight runs
   (angle ≈ 180°) place a plain post.
4. **Balcony/stairs posts**: inherit automatically via the railing module;
   spot-check balcony grouped path (`balcony_types.py:136-162`).
5. **Audit sweep**: grep for `local_xyz(face)`, axis assumptions
   (`.x`/`.y` on world coords) in `floor_types.py`, `railing.py`,
   `balcony_types.py`, `stairs_types.py`; convert any found to local-frame math;
   file follow-ups for stragglers.

## Acceptance Criteria

- Columns place cleanly on a circular floorplan (no exception) at user-set
  spacing; column faces tag to `COLUMNS` group.
- Balcony corner posts on curved walls sit plumb and centered at each rail joint.
- Flat/90° behavior unchanged.

## Test Plan

- Headless: circular floorplan (n-gon with 32 verts) → floors with columns →
  assert build returns FINISHED and `COLUMNS` group non-empty.
- Railing on a semicircular balcony → assert each post vert lies within
  tolerance of the joint bisector ray.

## Risks

- Medium: touches shared helpers used by multiple modules; land behind the
  utility functions first, then migrate callers one module per PR.
- Coordinate with PR #230 which also edits `floor_types.py` (rebase order:
  land #230 cleanup first or vice versa).

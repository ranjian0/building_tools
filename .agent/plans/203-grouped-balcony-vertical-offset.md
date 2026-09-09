# Plan: Grouped balconies with railing don't offset vertically (#203)

- **Issue**: https://github.com/ranjian0/building_tools/issues/203
- **Type**: Bug
- **Symptom**: Multiple grouped balconies on a curved wall snap to the top edge
  of the target slab face; changing the vertical `size_offset.offset.y` has no effect
  when railing is enabled.

## Problem

Grouped balcony creation transforms the duplicated face group **before**
extruding, and the vertical offset path is gated/clamped in
`transform_grouped_faces`. When `has_railing` is on, an additional
`dissolve_faces` on the extruded top faces happens afterwards, but the reported
behavior shows the offset itself is lost — the balcony lands flush with the top
of the selection regardless of the offset value.

## Current Code State

- `btools/building/balcony/balcony_types.py:34-51` `create_balcony_grouped`:
  duplicates faces → `transform_grouped_faces` → `extrude_balcony_grouped` →
  railing via `add_railing_to_balcony_grouped`.
- `btools/building/balcony/balcony_types.py:200-215` `transform_grouped_faces`:
  - `clamped_offset = clamp(prop.size_offset.offset.y, 0.0, face_height - prop.height)`
  - moves **all group verts** up by `clamped_offset`.
  - The clamp lower bound `0.0` forbids offsets that push the balcony below the
    face bottom — but combined with the face-height measurement on curved walls
    (`calc_face_dimensions(f)[1]` of a large curved face returns its full height),
    any meaningful offset clamps to a value that visually does nothing, or to 0.
- `btools/building/balcony/balcony_types.py:83-107` `extrude_balcony_grouped`:
  insets in `splitones(depth)` steps; on **curved** (multi-face-normal) groups
  `f.normal.to_tuple(3) in valid_normals` can drop faces from the inset result,
  leaving the top-face set incomplete → later `dissolve_faces(...)["region"].pop()`
  (line 49) misidentifies the top face; the railing then sits at the slab top.
- The ungrouped path (`create_balcony_split`, lines 171-197) handles offsets
  with an explicit `-(face_h - height)/2` correction — the grouped path lacks
  the equivalent anchor-to-selection-bottom logic.

## Implementation Steps

1. **Anchor semantics**: define grouped balcony placement as "height H above the
   **bottom edge** of the selection + offset". Compute the group's bottom Z from
   vertex bounds (not `calc_face_dimensions`, which is unreliable on curved faces)
   and apply `translate(VEC_UP * (offset + height - face_height))` — mirroring
   the ungrouped correction — instead of clamping the raw offset into an
   effectively-zero band.
2. **Fix top-face collection in `extrude_balcony_grouped`**: don't filter inset
   results by normal equality; collect `res["faces"]` with `normal.z > 0` only
   (the function already does this for `result`), and use that same set for the
   railing's `dissolve_faces` input so the railing base is the real balcony top.
3. **Clamp with real bounds**: replace
   `clamp(prop.size_offset.offset.y, 0.0, face_height - prop.height)` with bounds
   derived from vertex min/max Z so curved walls behave like flat ones.
4. Verify the railing path (`add_railing_to_balcony_grouped`, lines 136-162)
   uses the moved geometry (it duplicates `top` after transform — should inherit
   the fix automatically once (1)–(2) land).

## Acceptance Criteria

- Grouped balconies on a curved wall: `offset.y = 2m` moves the balcony 2m up
  from the bottom of the selection, with and without railing.
- Offset persists when re-running the operator with identical settings.
- No regression on flat walls (grouped + ungrouped).

## Test Plan

- Headless test: curved wall mesh (cylinder segment), run grouped balcony build
  with railing and offset; assert balcony top Z ≈ selection bottom Z + offset + height.

## Risks

- Changes placement for existing scenes that (mis)relied on the old clamp; the
  new behavior matches the documented "vertical offset" intent, note in changelog.

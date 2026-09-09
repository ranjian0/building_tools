# Plan: Hip roofs by defined angle (#208)

- **Issue**: https://github.com/ranjian0/building_tools/issues/208
- **Type**: Enhancement
- **Request**: Drive hip (and gable) roof slope by **angle** (degrees) or
  **percentage** (rise/run, 100% = 45°) instead of total height. (Stretch:
  per-edge slopes — noted as optional.)

## Current State

- `create_hip_roof` (`btools/building/roof/roof_types.py:108-136`):
  `height_scale = prop.height / max([arc.height for arc in skeleton])` — the
  tallest arc is normalized to `prop.height`; other arcs scale proportionally,
  which yields a **uniform pitch** already (straight skeleton property: all
  arcs grow at rate 1 in skeleton time).
- Therefore: slope angle is currently an *output* (derived from footprint shape
  + height), not an *input*. Converting is straightforward:
  `height = tan(pitch) * skeleton_time`, i.e. `height_scale = tan(radians(angle))`
  directly — the max-arc normalization can be replaced.

## Implementation Steps

1. **Props** (`roof_props.py`): add
   `slope_mode: EnumProperty items=[HEIGHT, ANGLE, PERCENTAGE]` and
   `slope_angle: FloatProperty(subtype="ANGLE", min=5°, max=75°)`,
   `slope_percentage: FloatProperty(min=5, max=500, subtype="PERCENTAGE" or plain)`.
   Draw conditionally per mode (pattern exists in `draw()`).
2. **Conversion helper** in `roof_types.py`:
   `slope_to_height_scale(prop) -> float`:
   - HEIGHT → `prop.height / max(arc heights)` (current behavior)
   - ANGLE → `tan(slope_angle)`
   - PERCENTAGE → `tan(atan(pct / 100))` = `pct/100`
3. Apply in `create_hip_roof` and `create_gable_roof` (gables have a uniform
   slope along the ridge direction — same formula, capped so the ridge stays
   above 0 for narrow plans: if computed ridge height ≤ 0, clamp with warning).
4. **Back-compat**: default `slope_mode = HEIGHT` so existing scenes/presets
   behave identically.
5. **UI**: show the *effective* height next to the angle field (computed from
   max arc) so users keep spatial awareness.
6. **Stretch (defer)**: per-edge slope override — select base edges before
   invoking; store per-edge slope in an edge float layer and use a
   non-uniform skeleton weighting. This needs modifications in
   `util_skeleton.py` (weighted skeleton variant) — file as a follow-up issue
   referencing #208 rather than blocking this plan.

## Acceptance Criteria

- Hip roof with ANGLE=45° on a square footprint: each roof plane rises at 45°
  (measurable: face normal z ≈ cos45°).
- PERCENTAGE=50 gives exactly half the rise of 100% on the same footprint.
- HEIGHT mode unchanged (regression).

## Test Plan

- Headless: square footprint 10×10, angle 45° → assert apex height ≈ 5
  (inradius × tan45°); percentage 50 → apex ≈ 2.5.

## Risks

- Narrow footprints with steep angles can push apex absurdly high — add a soft
  cap (e.g. `max_height` prop, default off).
- Shares the `height_scale_fn` refactor from `040-new-roof-types.md` —
  coordinate landing order (this one first, it's smaller).

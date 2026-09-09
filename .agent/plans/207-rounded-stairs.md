# Plan: Rounded staircase types (#207)

- **Issue**: https://github.com/ranjian0/building_tools/issues/207
- **Type**: Enhancement
- **Request**: Spiral and winder (curved/rounded) stairs in addition to the
  straight types.

## Current State

- `btools/building/stairs/stairs_types.py:31+` `create_stairs` builds straight
  runs: `create_steps` → filled / blocked / slope step styles
  (lines 69/100/139), with landing support and railing
  (`add_railing_to_stairs`, line 255).
- Stairs are placed from a **selected vertical wall face**; props in
  `stairs_props.py` (step count/width/height, landing width, type enum for step style).
- No curved-geometry helpers exist in the stairs module.

## Design

### Type A — Spiral stairs (new operator, not face-based)

Spiral stairs need a center + radius, not a wall face. Options:

- (a) Keep face-based: derive center from the selected face's horizontal axis —
  limiting and unintuitive.
- (b) **Object-mode operator with a modal placement click** (like road tools'
  click-based flow, `btools/road/`): click sets center, move sets
  radius/rotation, click again confirms. Recommended.

Props: `inner_radius`, `total_rotation` (default 270°), `floor_height`,
`step_count` (auto from height/2-space rule with `step_height`), `direction`
(CW/CCW), `has_center_column` (cylinder post).

Geometry: each step = wedge (pie slice) between `angle_i` and `angle_i+1`,
extruded at increasing Z; center column via cylinder; railing: helix of posts +
sloped handrail segments between post tops (reuse rail fill builders from
`btools/building/railing/`).

### Type B — Winder stairs (extension of straight run)

Winders = pie-shaped steps at the turn of an L-shaped run.

1. Add `stairs_type` enum: `STRAIGHT | WINDER_L` (v1: single 90° turn).
2. Straight run to `landing_width` before the turn, then N wedge steps in the
   corner (angle share configurable: `winder_balance` 0.5 = even), then the
   second straight run perpendicular — all from the same selected face when the
   face is wide enough; document the required face shape.
3. Railing follows run edges — reuse `add_railing_to_stairs` per segment.

## Implementation Steps

1. Shared wedge-step helper `create_wedge_step(bm, center, r0, r1, a0, a1, z)`
   in `stairs_types.py` (used by both types).
2. Spiral: props + object-mode operator (`stairs/spiral_ops.py`), matgroups
   (`STAIRS`, plus railing groups via existing railing module), PRESET support.
3. Winder: extend enum + split logic in `create_stairs`; keep straight path
   untouched for `STRAIGHT`.
4. both: headless-safe (no modal dependency for tests — operator accepts
   explicit center/radius overrides via properties).

## Acceptance Criteria

- Spiral stair: wedge steps ascend at consistent rise; railing continuous;
  CW/CCW work; center column optional.
- Winder L: turn steps meet at 90°, no gaps/overlaps; straight type unchanged.

## Test Plan

- Headless: build spiral with fixed center/radius → assert step count =
  ceil(floor_height / step_height) and all step tops within tolerance of
  expected Z; winder build on wide face → assert FINISHED and step z monotonic.

## Risks

- Modal operator UX is new to this addon (road module is precedent).
- Railing on helix is fiddly; acceptable v1: posts only, handrail optional flag.

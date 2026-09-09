# Plan: Porch object (#190)

- **Issue**: https://github.com/ranjian0/building_tools/issues/190
- **Type**: Enhancement
- **Request**: A "Porch" object (the reporter currently combines balcony +
  stairs manually). Also mentions shutters (covered by
  `209-window-shutters.md`).

## Design

A porch = **roofed platform at door level** composed of existing primitives:

- deck/floor slab (balcony-like extrusion),
- support columns (reuses the columns work from #226),
- railing (existing railing module),
- small shed/gable roof over the platform (roof module),
- optional steps down (stairs module).

Two implementation strategies:

### Strategy A (recommended) — Composite/"preset" operator, no new geometry engine

`BTOOLS_OT_add_porch` (edit mode, select the wall face(s) at door level):

1. Build platform: extrude face outward `depth`, up `platform_height`
   (balcony logic: `balcony_types.py:72-80` `extrude_balcony` as reference).
2. Add `roof_type` option [FLAT, GABLE, SHED] over the platform (call
   `create_roof` on the platform top face with a `RoofProperty` clone seeded
   from props).
3. Columns at platform corners when `has_columns` (floor_types column builder).
4. Railing around the perimeter when `has_railing` (railing module), leaving
   the wall side open.
5. Optional steps: `add_steps` → run stairs builder on the front edge
   (stairs_types straight run).
6. All parts tagged with their standard matgroups so #210 defaults work.

This is mostly **composition of existing tested builders** — low risk, high
reuse, and matches how the issue author already hacks it together.

### Strategy B — Dedicated porch generator

Custom monolithic generator with unified props. More control (integrated
roof-wall junction, header beam), but duplicates logic. Defer; revisit if
Strategy A hits composition limits (e.g. roof needs to attach to the wall).

## Props (PorchProperty)

- `depth`, `platform_height` (relative to face bottom), `roof_type`,
  `roof_height`, `has_columns`, `column_width`, `has_railing`, `add_steps`,
  `step_count`.

## Implementation Steps

1. `btools/building/porch/` module (props/ops/types), panel button under
   balcony, register in `register.py`, API options class.
2. Implement Strategy A pipeline; each sub-builder already tags its own faces.
3. Presets: "Front Porch", "Covered Entry".

## Acceptance Criteria

- One click on a ground-floor wall face produces platform + roof + columns +
  steps, each editable via its native tool afterward (they're standard
  geometry + matgroups).

## Test Plan

- Headless: porch on flat wall → assert FINISHED, platform top z =
  platform_height, roof faces tagged ROOF, steps ascend below platform.

## Risks

- Composited roof on the platform needs the wall-face → roof-face handoff
  (active-face selection inside bmesh, not viewport) — manageable since all
  builders take face lists directly.
- Depends on #226 corner-frame work for clean column placement on non-90°
  platforms (soft dependency; 90° porches fine without).

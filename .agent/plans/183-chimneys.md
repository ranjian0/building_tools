# Plan: Chimneys (#183)

- **Issue**: https://github.com/ranjian0/building_tools/issues/183
- **Type**: Enhancement
- **Request**: Add chimneys to roofs (domestic + industrial styles; reference
  images in issue).

## Design

Two placement modes, mirroring the addon's existing UX patterns:

### Mode 1 — Roof-integrated (edit mode)

Operator `BTOOLS_OT_add_chimney` (edit mode, face-based like other building
ops): select roof face(s) where the chimney passes through; creates:

- stacked brick shaft through the roof (top/bottom extension props),
- cap slab + optional pot(s) (`pot_count`, cylindrical),
- roof flashing skirt (small outset ring at the penetration),
- tags: new `MaterialGroup.CHIMNEY`? — prefer reusing `WALLS` (brick) +
  `ROOF` (flashing) to avoid enum churn; revisit with #210 defaults.

### Mode 2 — Decorative placement (object mode)

Simple "place on clicked roof point" operator, like the spiral-stairs plan
(207) modal flow — optional Phase 2; Mode 1 covers the core request.

## Props (ChimneyProperty)

- `width`, `depth` (shaft cross-section), `height_above_roof`,
  `height_below_roof` (for interior continuation),
- `cap` bool + `cap_outset`, `pot_count` (0–4) + `pot_radius`,
- `flashing` bool,
- `style: EnumProperty [BRICK, INDUSTRIAL]` — industrial = wider cylinder +
  band rings (bands via inset-extrude loops).

## Implementation Steps

1. `btools/building/chimney/` module following the standard
   props/ops/types/__init__ pattern; register in `register.py` + panel button
   in `__init__.py` (grouped with roof row).
2. Geometry: shaft as extruded rectangle from the selected face plane; cut
   nothing (roof faces stay — shaft sits on top, simplest and non-destructive);
   optional "cut hole" bool later (needs careful face ops — defer).
3. Intersection safety: clamp shaft base to face bounds; if face too small,
   cancel with message (pattern: `validate_balcony_faces` in balcony_ops.py:59).
4. API options class in `btools/api/options.py` + registration in `api.py`.
5. Wiki page + presets ("Tall Brick", "Industrial").

## Acceptance Criteria

- Chimney builds on hip/gable/flat roof faces (any slope — shaft stays
  plumb), correct matgroup tagging, undo-safe, PRESET support.

## Test Plan

- Headless: hip roof → add chimney on a slope face → assert shaft top z >
  roof ridge? no — assert shaft extends `height_above_roof` above the face
  plane along +Z; flashing ring exists (extra face ring around shaft base).

## Risks

- Low; self-contained new module. Only shared touchpoint is the panel layout
  and `register.py`.

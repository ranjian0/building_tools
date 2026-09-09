# Plan: Batch generation from footprint attributes (#214)

- **Issue**: https://github.com/ranjian0/building_tools/issues/214
- **Type**: Enhancement
- **Use case**: City-scale generation: many flat footprint objects (imported via
  BlenderGIS/OSM with **custom properties** like `Roof Form`, `EaveHeight`)
  should get floors, roofs, and windows automatically.

## Current State

- A headless-capable Python API already exists: `btools/api/api.py`
  (`create_floorplan`, `create_floors`, `create_roof`, `create_window`, ...)
  driven by dataclass options (`btools/api/options.py`).
- Nothing iterates over a scene's objects or reads object custom properties.
- No batch operator exists in the UI.

## Design

New module `btools/building/batch/` (props/ops pattern) + one operator:
**BTOOLS_OT_batch_generate** ("Batch Generate Buildings"):

1. Operates on selected mesh objects (each = one building footprint, XY flat).
2. Per-object attribute mapping (scene-level prop group with text fields):
   - `roof_type_attribute` (default `"Roof Form"`)
   - `roof_height_attribute` (default `"EaveHeight"`)
   - `floor_count_attribute`, `floor_height_attribute` (optional; #173 compat)
   - fallback values when attribute missing (defaults per field).
3. Attribute value mapping: string → roof enum (`"gable"→GABLE`, `"hip"→HIP`,
   `"flat"→FLAT`, `"pyramidal"→HIP`, case-insensitive prefix match; unmapped →
   fallback).
4. Per object pipeline (all via the existing `btools/api` functions so headless
   scripts get the same behavior for free):
   - duplicate footprint into a new building object (keep the footprint intact)
   - `create_floors(FloorOptions(floor_count=n, floor_height=h, ...))`
   - `create_roof(RoofOptions(type=mapped_type, height=..., ...))`
   - optional window pass: `create_window` on wall faces with probability
     `window_density` (0–1, default 0 → off), seeded RNG (ties to #163).
5. Progress bar + per-object error collection reported at the end
   (`self.report`) instead of aborting the batch.

## Implementation Steps

1. Add `btools/building/batch/batch_props.py` (attribute names, defaults,
   density, seed), `batch_ops.py` (operator + poll on selected mesh objects in
   object mode), register in `register.py`.
2. Validate footprints: skip non-flat meshes (any vert z ≠ 0 within epsilon)
   with a warning entry.
3. Ensure the `api.create_*` functions work when the addon UI operators
   haven't been used yet (they already self-register props via
   `register_property` — verify for floors/roof paths in a headless test).
4. Performance guard: process in a single `bpy.ops.ed.undo_push` per building;
   offer `dry_run` bool that only validates + reports.
5. Document the expected attribute schema in the wiki (align names with
   BlenderGIS/OSM exports and the issue's ArcGIS sample).

## Acceptance Criteria

- Selecting 50 footprint objects with `Roof Form`/`EaveHeight` props produces
  50 buildings with correct roof types/heights in one click; failures are
  reported per-object without stopping the batch.

## Test Plan

- Headless: generate 5 footprint objects with mixed attributes; run operator
  via `bpy.ops.btools.batch_generate()`; assert object count, roof enum match,
  and error list empty.

## Risks

- Attribute name guessing across GIS exporters — keep mapping user-editable.
- Complements `173-shapefile-driven-floorplans.md` (same engine, import-side
  differs) and `163-randomization-options.md` (window density randomness).

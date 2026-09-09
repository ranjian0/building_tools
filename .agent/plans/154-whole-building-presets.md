# Plan: Whole-building operator presets (#154)

- **Issue**: https://github.com/ranjian0/building_tools/issues/154
- **Type**: Enhancement (labeled **Medium Priority**)
- **Request**: Presets for the entire building, not just per-operator.

## Current State

- Each operator enables Blender's preset system via
  `bl_options = {"REGISTER", "UNDO", "PRESET"}` (e.g. `door_ops.py:26`) —
  presets serialize the operator's `props` PointerProperty chain, per operator only.
- Nothing cross-links settings between operators (floorplan ↔ floors ↔ roof ↔
  door/window...).

## Design

**Building-style presets**: a scene-level `BuildingStyleProperty` that mirrors
the component property groups, plus save/load to JSON stored in the addon
presets directory.

1. `btools/building/style.py`:
   - `BuildingStyleProperty` with pointers/duplicated fields for: floorplan,
     floor, roof, balcony, stairs, door, window, multigroup props
     (composition via `PointerProperty(type=...)` to the *existing* property
     groups keeps serialization automatic and avoids field duplication).
   - `BTOOLS_OT_style_save`: serialize active building's *last used* operator
     props (each op stashes its props dict on the object via custom property
     `btools_last_props` — add that stash line in each `build()`; keyed per
     component) into `presets/building_tools/<name>.json`.
   - `BTOOLS_OT_style_apply`: given a selected building (or before creation),
     apply the JSON into each component's property group; subsequent operator
     runs use those values (operators read their `props` which the user has
     just had pre-filled — implement by writing into the scene property groups
     used by the UI operators).
2. UI: "Building Presets" panel section (dropdown of saved styles + save
   button), placed at the top of the Building Tools panel.
3. Format: JSON via `dict_from_prop`/`prop_from_dict` (already exist in
   `btools/utils` and used by the API layer — round-trip support is free).
4. Ship 3–4 bundled styles (e.g. "Suburban", "Townhouse", "Industrial",
   "Mediterranean") as JSON files in `presets/`; add `presets/` to
   `scripts/make-release.py::REPO_FILES`.
5. Compatibility: version key in the JSON; unknown fields ignored on apply
   (forward-compatible loading).

## Implementation Steps

1. Add prop-stash (`btools_last_props`) in each component `build()` — small,
   mechanical change per module; needed so "save current building style" has a
   source of truth.
2. Style property group + save/apply operators + panel.
3. Bundled presets + release-script packaging.
4. Document in wiki ("Building Presets").

## Acceptance Criteria

- User configures a full building across operators → saves style → starts a
  new floorplan → applies style → all panels show the saved values; next
  operator invocations use them.
- Presets survive addon restart (stored on disk).

## Test Plan

- Headless: set floorplan/roof props, save style, reset props, apply style,
  assert round-trip equality of all serialized fields.

## Risks

- Property-group evolution can orphan fields — the version key + lenient
  loading handles it.
- Ties into #39 Phase 3 (operator presets packaging) and #214 (styles could
  feed batch generation attributes).

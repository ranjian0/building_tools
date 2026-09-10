# Plan: Building Presets — API recipes + Complete Buildings panel

**Status**: Done (v1 shipped on `feature/reference-corpus`)
**Goal**: One-click complete buildings for users, composed from the
scriptable api; a dedicated panel to pick, tweak and build them.

## Research summary

- Archetype study (CityEngine CGA grammars, Metropolygonia, PBG kits) shows a
  two-layer decomposition: **massing** (footprint × storeys × roof) +
  **façade pattern** (opening grid × fills × balconies) — maps 1:1 onto the
  addon's primitives.
- 11 archetypes evaluated against the primitive set; 8 fit for v1. Gaps
  recorded: dormers, chimneys, awnings/signage, tapered roofs (church/civic
  and gas station excluded).
- Reference images (verified Wikimedia Commons links) are embedded per
  preset in `btools/api/presets.py::reference`.

## Implementation

- `btools/api/select.py` — face-selection library promoted from the session
  tooling into the addon: world-space selectors, storey-band filtering,
  material-group filters, deterministic area ordering.
- `btools/api/presets.py` — `BuildingPreset`/`FacadeRule` dataclasses +
  `PRESETS` registry + `build_preset(preset, floors, width_scale,
  depth_scale) -> OpResult`. Facade rules target selector names per storey;
  within-face repetition uses the features' own `array` options.
- UI: `BTOOLS_PT_building_presets` panel + `BTOOLS_OT_build_preset` +
  `BTOOLS_PresetSettings` scene group (root `__init__.py`); thumbnails
  bundled in `btools/presets/thumbs/` (rendered by `bt thumbs` with the
  reference camera/material pipeline).
- Verification: 8 `preset-*` corpus cases (JSON + render, all contracts
  green) + `TestPresets` headless test.

## Findings during implementation

- `multigroup + add_arch` is broken at all sizes
  (`create_arch` connect_verts pop-empty) — documented as corpus case
  `multigroup-arch`, known issue `multigroup_arch_broken`.
- Door/window `add_arch` is mesh-state dependent (flaky) — markers
  `flaky_arch_unpack` / `flaky_louver_max_empty`.
- Blender 5.x removed `bpy.utils.previews` — panel dropdown is text-only;
  thumbnails remain bundled for docs/gallery until an icon path is chosen.

## Follow-ups

- Re-add arched openings to mediterranean-villa once arch generation is
  stable.
- Preset randomization hooks (#163) and batch payload (#214) reuse
  `build_preset`.
- Per-storey options (e.g. pilotis ground floor) need floors-op changes.

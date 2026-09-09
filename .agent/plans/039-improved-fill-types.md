# Plan: Improved fill types (#39)

- **Issue**: https://github.com/ranjian0/building_tools/issues/39
- **Type**: Enhancement (labeled **High Priority**)
- **Goal**: More fill types + quick presets for common combinations, guided by
  the reference imagery in the issue (window/door fill examples).

## Current State

Fill system lives in `btools/building/fill/`:

- `fill_props.py:201-242` `FillProperty` — enum
  `PANELS | GLASS_PANES | LOUVER | BAR`, pointer props per type, `draw()` maps
  type → sub-panel.
- `fill_types.py:28-115` — `add_fill`, `get_fill_type`, `fill_face`,
  `validate_fill_props` dispatch; type builders: `fill_panel` (117),
  `fill_glass_panes` (148), `fill_bar` (181), `fill_louver` (223).
- Consumers: door/window/multigroup each embed a `FillProperty`
  (`door_props.py`, `window_props.py`, `multigroup_props.py`) and call
  `fill_face(bm, face, prop, dw)`.
- The API layer registers fill classes manually (`btools/api/api.py:70-74,106-110,140-145`) —
  every new fill class must also be added there.

## Task List from the Issue

Diamond, Cross Panel, Full Louver, Upper Louver, Lower Louver, Split Louver,
Half Glass (1/2/3/4 panel), Half Glass 2/3 panel horizontal.

## Implementation Steps

### Phase 1 — Louver variants (cheap: parameterize existing `fill_louver`)

1. Add a `louver_direction` enum to `FillLouver`
   (`fill_props.py`): `FULL | UPPER | LOWER` (and `SPLIT` = both, meeting in
   the middle). Implement by splitting the arch face horizontally
   (`subdivide_face_vertically` already in `util_mesh.py`) and running the
   existing louver routine on the selected band(s).
2. Map to issue items: Full Louver, Upper Louver, Lower Louver, Split Louver —
   4 items closed with one parameter.

### Phase 2 — Panel variants

3. `FillPanel` gains a `panel_style` enum: `PLAIN | DIAMOND | CROSS`:
   - **Cross Panel**: diagonal bars across the recessed panel (two corner-to-corner
     bars reusing `create_bar_from_face` with rotation).
   - **Diamond**: same bar routine rotated 45°, clipped to panel bounds.
4. Half Glass family: parameterize `FillGlassPanes` with `glass_layout`:
   `FULL | HALF_LOWER | HALF_UPPER` + `panel_count` (1–4, horizontal/vertical
   toggle). Reuse `subdivide_face_into_quads` (fill_types.py:254) for the glass
   region and keep lower/upper half solid panel.

### Phase 3 — Presets

5. Add Blender operator presets support where missing (`bl_options = {"PRESET"}` —
   door/window already have it; verify fill sub-props serialize — they do, as
   they're part of the operator's `props` PointerProperty chain).
6. Ship bundled presets: create `presets/door/*.py` + `presets/window/*.py`
   in the addon (packaged via `scripts/make-release.py` — add `presets/` to
   `REPO_FILES`) with common styles from the issue's reference images
   (e.g. "Louvered Door", "4-Panel Picture Window", "Diamond Cottage").

### Phase 4 — Validation & docs

7. Extend `validate_fill_props` (fill_types.py:84) per new type (min/max sizes).
8. Update API `options.py` dataclasses (`btools/api/options.py`) with the new
   fields and register new property classes in `api.py`.
9. Wiki docs per fill type with screenshot; reference issue #39 in PRs and tick
   items as they land.

## Acceptance Criteria

- All 13 checklist items from the issue are selectable and render correctly on
  door and window faces.
- Old scenes keep their fill settings (enum items appended, never reordered —
  Blender enums are stored by identifier, safe).

## Test Plan

- Headless test iterating each new enum combination on a wall with a door +
  window; assert FINISHED and no untagged faces.

## Risks

- UI clutter in the fill panel as options grow; mitigate with per-type
  conditional `draw()` (pattern already exists in `FillProperty.draw`).

# Plan: Window shutters (#209, also requested in #190)

- **Issues**:
  - https://github.com/ranjian0/building_tools/issues/209 (Dutch/Mediterranean shutters, with reference images + video)
  - https://github.com/ranjian0/building_tools/issues/190 ("include window shutters in window props would be great too")
- **Type**: Enhancement

## Concept

Decorative (optionally operable-looking) shutter panels mounted on the wall
beside a window — classic Dutch `luiken` (flat planked panels, often painted)
and Mediterranean variants (louvered, sometimes with brackets).

## Current State

- Windows: `btools/building/window/window_props.py` (WindowProperty with frame,
  fills, arch, array) and `window_types.py` (`create_window`, window split,
  frame via `btools/building/frame.py`).
- Louver fill builder exists: `btools/building/fill/fill_types.py:223`
  `fill_louver` — reusable for louvered shutters.
- No side-mounted decoration concept exists; nearest analog is the balcony
  (side extrusion) and custom objects (#222).

## Design

New `ShutterProperty` group embedded in `WindowProperty`:

- `has_shutters: BoolProperty`
- `shutter_type: EnumProperty [PLANKED, LOUVERED]`
- `width` (fraction of window width, default 0.4), `depth` (panel thickness),
- `open_angle` (0° closed flush → up to ~160° fully open; 0 = flat on wall),
- `include_top_bar` / bracket option (Mediterranean look) — follow-up.

Geometry (per side, left/right of the window split, on the wall face plane):

1. After the window split is computed (`window_types.py` window split
   equivalent of `create_split`), take the wall regions adjacent to the frame.
2. Create panel face of `width × frame_height + margin`, inset border for
   planked style (or apply `fill_louver` internals for louvered style).
3. Rotate around the panel's window-side vertical edge by `open_angle` into
   the wall normal direction; angled panels need the wall to be locally flat —
   if the source face is curved (adjacent normals differ), clamp `open_angle`
   to 0 with a console note (v1).
4. Tag panels + louvers to the FRAME matgroup (painted-wood role) or a new
   `SHUTTER` group — prefer **FRAME** to avoid enum-compat churn; revisit if
   #210 default materials want a distinct color.

## Implementation Steps

1. `shutter_props.py` + embed + `draw()` section (collapsed by default).
2. `create_shutters(bm, face, window_region, prop)` in new
   `window/shutter_types.py`; call at the end of `create_window` when enabled.
3. Planked style: inset + a few horizontal groove cuts (knife/inset strips).
   Louvered style: factor `fill_louver` core (fill_types.py:223-253) into a
   reusable `make_louver_band(bm, face, count, depth, angle)` used by both
   fill and shutter paths.
4. Array support comes free via the existing window `count` array (shutters
   generated per window instance).
5. Presets: "Dutch Planked", "Mediterranean Louvered" (ties into #39 Phase 3).
6. Wiki section + reference the issue photos.

## Acceptance Criteria

- Dutch window: two flat planked panels flank the frame at settable width;
  open_angle rotates both panels outward symmetrically; survives undo and
  matgroup select.

## Test Plan

- Headless: wall + window with shutters → assert 2 panel clusters, panels'
  verts on the wall plane when `open_angle=0`, rotated about correct hinge edge
  at 90°.

## Risks

- Interaction with window array on curved walls — v1 restricts shutters to
  flat faces (guard + message), matching the custom-object limitation style.

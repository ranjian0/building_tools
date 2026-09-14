# Building Tools — Work Plans

Plans for addressing all currently open issues and pull requests.
Each plan file is named after its issue/PR number and contains: problem summary,
current code state, proposed implementation steps, acceptance criteria, and risks.

Source repo: https://github.com/ranjian0/building_tools

## Infrastructure plans

- [api-control-surface](api-control-surface.md) — scriptable, deterministic
  operations (`btools/api`) + `bt api`/`bt validate`/`bt scenario` commands.
  **Done**.
- [building-presets](building-presets.md) — complete-building presets
  (`btools/api/presets.py`) + Building Presets panel + thumbnails.
  **Done (v1)**.
- [research-building-algorithms](research-building-algorithms.md) — research
  reference: procedural building-modeling algorithms (skeleton family,
  grammars, layout partitioning, GIS/LoD pipelines) mapped to open issues
  with an adopt-first ranking.

## Status Snapshot (2026-09)

- Addon version: `v1.0.13`, Blender 4.x compatible (min `3.3` in `bl_info`)
- 28 open issues (8 bugs, 20 enhancements), 1 open PR
- Test harness: `just test` (runs `tests/__main__.py` inside Blender)
- Lint/typecheck: `just format` (black), `just check` (mypy), `just lint` (ruff)
- Tooling: uv (venv + lockfile), just (task runner)

## Priority Order

### P0 — Bugs (user-facing breakage)

| Plan | Issue | Title |
|------|-------|-------|
| [221](221-blender-40-activation-error.md) | #221 | Can't activate in Blender 4.0.2 (registration error) |
| [222](222-custom-geometry-errors.md) | #222 | Custom geometry deformed / offset / fails |
| [203](203-grouped-balcony-vertical-offset.md) | #203 | Grouped balconies with railing don't offset vertically |
| [228](228-gable-roof-wall-tagging.md) | #228 | Gable roof wall face not tagged as wall |
| [229](229-balcony-inverted-normals.md) | #229 | Balconies create inverted face normals |
| [204](204-inverted-wall-depth.md) | #204 | Depth issues on inverted walls |
| [226](226-corner-elements-non-right-angles.md) | #226 | Corner elements only work for 90° (High Priority label) |

### P0 — Open PR

| Plan | PR | Title |
|------|----|-------|
| [pr230](pr230-mansard-roof.md) | #230 | Mansard roof type (needs cleanup + finishing before merge) |

### P1 — High-value enhancements (tracked issues with priority labels)

| Plan | Issue | Title |
|------|-------|-------|
| [039](039-improved-fill-types.md) | #39 | Improved fill types (High Priority) |
| [040](040-new-roof-types.md) | #40 | New roof types: mansard, gambrel, dutch hip/gable (Medium) |
| [166](166-extra-balcony-features.md) | #166 | Extra balcony features (Medium) |
| [154](154-whole-building-presets.md) | #154 | Operator presets for entire building (Medium) |

### P2 — Enhancements with clear scope

| Plan | Issue | Title |
|------|-------|-------|
| [208](208-hip-roof-by-angle.md) | #208 | Hip roofs by defined angle/percentage |
| [187](187-multi-face-roofs.md) | #187 | Generate roofs on multiple faces at once |
| [103](103-floorplan-holes.md) | #103 | Support floorplans with holes |
| [214](214-batch-generation.md) | #214 | Batch generation from footprint attributes |
| [173](173-shapefile-driven-floorplans.md) | #173 | Floors/footprints from shapefile/GIS data |
| [212](212-toolbar-buttons-docs.md) | #212 | Document the three toolbar buttons |
| [210](210-default-materials.md) | #210 | Default materials for face-map groups |

### P3 — New feature areas (larger, multi-release)

| Plan | Issue | Title |
|------|-------|-------|
| [202 + 217](202-217-interior-walls.md) | #202, #217 | Interior walls / interiors |
| [207](207-rounded-stairs.md) | #207 | Spiral / winder (rounded) staircases |
| [209](209-window-shutters.md) | #209, (part of #190) | Window shutters |
| [183](183-chimneys.md) | #183 | Chimneys |
| [126](126-rain-gutters.md) | #126 | Rain gutters |
| [190](190-porch.md) | #190 | Porch object |
| [163](163-randomization-options.md) | #163 | Randomization with master decision list |

## Suggested Milestone Grouping

1. **v1.0.14 (bugfix)** — #221, #203, #228, #229, #204, #222, plus review/merge PR #230 (#226 is larger, lands in the release after)
2. **v1.1 (features)** — PR #230 finished output (mansard), #208, #187, #39 (first batch of fills), #154, #212, #210
3. **v1.2+** — #103, #214, #173, #166, #226 refactor, then P3 items

## Conventions used in plans

- Code references are `file:line` at the time of writing (commit `0216534`).
- Every bug plan includes a manual reproduction recipe and, where feasible, a
  headless test to add under `tests/` (run with `just test`).
- Every feature plan lists the property-group, operator, and geometry-function
  files that need touching, following the existing module layout
  (`*_props.py` / `*_ops.py` / `*_types.py`).

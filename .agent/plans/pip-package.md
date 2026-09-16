# Plan: pip-package pivot (2.0)

**Branch**: `feature/pip-package`
**Goal**: `pip install building-tools[bpy]` → AI agents write rule files,
run them headless, confirm with renders, export production assets.

## Decisions (user, 2026-09)

- Name: **building-tools** (import stays `btools`; PyPI `btools` taken)
- **Hard pivot**: the Blender addon wrapper is deleted; users on the
  panel UI stay on v1.0.13 releases
- **bpy==5.1.2 is a hard dependency** (pinned, not an extra): the
  geometry code targets these exact APIs
- Rule files: **Python only** (the JSON layer is deferred)
- MVP first: phases 1-3 (package + registration + CLI + rule contract)

## Audit findings (what made this cheap)

- The geometry pipeline, all presets, PBR materials, glb/fbx export and
  Workbench/EEVEE/Cycles renders already work headless under the pip
  bpy wheel (verified by probes, see the session log)
- The api only needs ~25 lines of registration: REGISTER_ORDER
  PropertyGroups + BTMaterial + Object.bt_materials(+index)
- `btools/__init__.py` was empty; the addon wrapper never imported by
  the api path

## Landed (phase 1-3)

- pyproject: hatchling wheel (packages=["btools"]), hard bpy pin,
  `btools = btools.cli:main` console script, lint group (mypy/ruff/
  fake-bpy-module); `[tool.uv] package=false` removed
- `btools/__init__.py`: `register()` (idempotent; register_building +
  detail level) / `unregister()` / `ensure_registered()`
- `btools/cli.py`: run / preset / list-presets / smoke; --render
  --views --engine --res --ascii --export (repeatable) --json --seed;
  exit 0 iff all OpResults ok
- `btools/rules.py`: RuleContext (floorplan/floors/roof/interior/
  windows/doors/feature/preset/batch/rng/ascii/export/render) — the
  rule-file vocabulary; `_record` tracks created objects +
  OpResult.decisions
- `btools/render.py`: ortho camera + light rig over scene bounds,
  engine fallback chain (EEVEE -> Workbench -> Cycles), multi-view
  render_views
- `examples/house.py`: documented example rule file
- docs/RULES.md: the rule-file vocabulary reference
- tests/__main__.py migrated OFF LoadModule: `import btools;
  btools.register()` (single namespace, no more dual-class bugs)
- tests/test_cli.py: list-presets JSON, preset+render artifacts,
  rule-file execution

## Known gaps (follow-ups)

- UV auto-projection is skipped headless (`util_material.py` guard) —
  exports have no UV maps; try smart-project under pip bpy or document
- `btools smoke` replaces `bt smoke`; the reference-corpus PNG
  baselines were rendered by the GUI session — regenerating them
  headless via `btools render` is a follow-up (geometry hashes
  unchanged)
- `.agent/tools` GUI sessions (bt start/reload/screenshots) are legacy:
  the addon wrapper is gone from the tree; manual GUI exploration uses
  old releases; visual QA now via `btools render` + media analysis
- Blender addon users: direct them to the v1.0.13 release (frozen)

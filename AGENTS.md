# AGENTS.md

Guide for AI coding agents working on **Building Tools** — a procedural
building-generation package for Blender's Python API, distributed as the
`building-tools` pip package and driven by AI agents through rule files.

**Branch `feature/pip-package` pivoted the project to a pip package**
(2.0.0a0): `bpy==5.1.2` is a hard dependency, the Blender addon UI is
legacy (frozen at v1.0.13 releases), and the agent surface is
`btools.api` + `btools run <rule.py>` + headless renders/exports.

## Project layout

```
btools/                # THE pip package (installed as building-tools)
  __init__.py          # version + register()/unregister() bootstrap
  cli.py               # btools CLI (run/preset/list-presets/smoke)
  rules.py             # RuleContext handed to rule files
  render.py            # headless confirmation renders (engine fallback)
  api/                 # scriptable surface (the ONLY stable path)
    core.py            # FaceTarget, runners, _edit_session (normalize=...)
    options.py         # typed dataclasses per feature (drift-tested)
    presets.py         # 8 bundled presets + build_preset
    batch.py           # generate_batch from footprint attributes
    result.py          # OpResult dataclass (status, matgroups, errors)
    select.py          # world-space face selectors
    facade.py          # bay-grid facade layer
    validate.py        # matgroup/geometry/normal reports
    probe.py           # measurements, ASCII elevations, interpenetration
    checks.py          # declarative preset checks
    export/__init__.py # glb/fbx production export (semantic slots)
  building/<feature>/  # one dir per feature: *_props.py, *_ops.py, *_types.py
    materialgroup.py   MaterialGroup enum, face-int-layer tagging, restore pass
    default_materials.py  BT_ PBR node materials per matgroup
    frame.py           shared frame-depth + sill/threshold helpers
    generator.py       legacy random building generator (api-adjacent)
  utils/               shared helpers (bmesh, geometry, layout, randomizer)
  road/                legacy road tool (unregistered, pending removal)
.agent/                dev tooling: bt GUI sessions (legacy), plans, corpus
docs/                  Jekyll site (artist docs) + RULES.md (rule vocabulary)
examples/              example rule files
tests/                 headless suite (runs via the bpy pip module)
```

## Environment & commands

`uv` manages the venv/lockfile (Python 3.13, pinned for the `bpy` wheel);
`just` is the task runner. Formatting is **ruff only** (no black).

| Command | Purpose |
|---------|---------|
| `just test` | headless test suite via bpy module (no window) — **run after every change** |
| `just test-blender` | same suite inside the Blender GUI (parity check) |
| `just check` | mypy |
| `just lint` | ruff check |
| `just format` | ruff format |
| `just sync` | (re)create the venv from the lockfile |
| `just build` / `just build-dev` | release zip from tag / latest commit |

The live-session toolkit lives in `.agent/tools/`:

```bash
.agent/tools/bt start        # GUI Blender on the 4K monitor (factory startup)
.agent/tools/bt reload       # hot-reload the addon from the working tree
.agent/tools/bt smoke        # build all 8 presets + validate + geometry checks — MANDATORY after building-code changes
.agent/tools/bt check --filter apartment          # declarative geometry checks for one preset
.agent/tools/bt check --elevation front           # ... plus an ASCII elevation readable as text
.agent/tools/bt api door --object wall --faces 1 --options '{"fill_type": "PANELS"}'
.agent/tools/bt validate --object wall --expect '{"groups": ["door", "frame"]}'
.agent/tools/bt scenario multi_storey
.agent/tools/bt reference generate --filter "preset-*"
.agent/tools/bt reference diff
.agent/tools/bt screenshot demo
.agent/tools/bt stop
```

Full reference: `.agent/tools/README.md` (session protocol, snippets,
Blender 5.1 gotchas).

## Geometry validation for agents (the reliable loop)

Agents without vision cannot trust image interpretation, and matgroup
counts are too coarse to catch spatial bugs. The reliable feedback loop
is **measurement** (`btools/api/probe.py`) + **declarative checks**
(`btools/api/checks.py`):

- `probe.measure_object(obj)` — storey bands, elevation bays (anchored
  on dominant wall planes), frame protrusions past wall planes, roof
  border outsets, per-storey group counts.
- `probe.group_intersections(a, b)` — EXACT edge-triangle crossings
  (immune to ray-parity leaks on open meshes and to coplanar touching;
  known limit: purely volumetric overlaps with only edge-on-plane
  contact read as 0).
- `probe.ascii_elevation(obj, view)` — raycast character grid (one char
  per matgroup + legend) readable directly in tool output. This is the
  agent's "eyes"; use `bt check --elevation front` to inspect a preset.
- `run_checks(obj, preset.checks)` — kinds: group_present,
  no_intersection, count_per_storey, bay_alignment, protrusion_range,
  symmetric_outset. `xfail: true` documents known defects with measured
  reasons; flip it off when fixed.

`bt smoke` runs every preset's checks (exit 1 on violation); `bt check`
re-runs them with failure details and optional ASCII views. When fixing
geometry: write the failing check first, then fix until it passes.

## Mandatory workflow for any change

1. Make the change.
2. `just format && just check && just lint`
3. `just test` — all tests must pass (60 as of the probe work; count drifts).
4. **`bt smoke`** — build all 8 presets + validate matgroup contracts +
   geometry checks; exit 1 on any failure. Run after ANY change to
   building code.
5. For anything geometry/visual: verify in the live session —

   ```bash
   bt restart && bt reload
   bt scenario multi_storey        # or wall / curved_wall
   bt api <feature> ...            # apply the change
   bt validate --object <name> --expect '{"groups": [...]}'
   bt exec viewport_setup.py && bt screenshot check
   ```

   `bt api`/`bt validate`/`bt scenario`/`bt check` emit JSON + exit
   codes — branch on those, not on prose. Use screenshots only for
   genuine visual judgment.

## Reference corpus (regression baseline)

`.agent/reference/` holds the committed baseline of what every tool
generates. Per case: a JSON log (options, matgroup counts, validation,
`geometry_hash`) + a **1280×1280 4-view EEVEE composite** (front/right/
top/iso in a 2×2 grid, matgroup-colored, flat lighting, cavity shading).

When fixing issues or adding features:

```bash
bt reference generate --filter "balcony*"   # subset or full sweep
bt reference diff                            # SEVERE/VISUAL = act; minor = noise
bt reference diff --update                   # promote the new baseline
```

Commit the updated baseline alongside the fix — the reference diff IS the
visual changelog. Known addon flaws are recorded per case in `known_issues`.

The composite layout: top-left = front elevation, top-right = right
elevation, bottom-left = top/plan, bottom-right = iso 3/4 (EEVEE with
soft sun + fill for PBR material depth).

## Scriptable api — the only scripted path

**Never drive `bpy.ops.btools.*` from scripts**: Blender resets operator
props to defaults on every scripted call. The supported surface is
`btools/api`:

```python
from btools.api import FloorplanOptions, RoofOptions, FaceTarget, apply_feature
from btools.api.presets import PRESETS, build_preset
from btools.api.validate import validate_object

r = apply_feature("floorplan", FloorplanOptions(width=10, length=8))
assert r.ok
obj = bpy.data.objects[r.created_object]

r = apply_feature("roof", RoofOptions(type="HIP", height=1.5),
                  FaceTarget(obj, [top_face_index]))
report = validate_object(obj, expect={"groups": ["walls", "roof"]})

# presets: complete buildings in one call
r = build_preset(PRESETS["suburban-house"])
```

- Options dataclasses (`btools/api/options.py`) are the single parameter
  format; `None` means "use the operator default".
- Every operation returns `OpResult` (`r.ok`, `r.errors`, `r.matgroup_counts`,
  `r.to_dict()`).
- `validate_object(obj, expect=...)` checks the addon's core contract: every
  face tagged to exactly one material group, plus optional group assertions.
  Geometry seams (door/window frame T-junctions) are common and advisory —
  pass `include_geometry=False` when gating on the contract.
- Presets (`presets.py`) compose floorplan + floors + roof + facade rules
  via `build_preset(PRESETS[id])`. Facade rules use world-space selectors
  from `btools/api/select.py` (front_walls, ground_front_wall, etc.).

### Import namespace (resolved on the pip pivot)

The addon-era dual namespace (building_tools vs btools) is gone: the
suite imports `btools.*` only, `tests/__main__.py` registers via
`btools.register()` (no more LoadModule), and per-test register_all()
calls are now guarded no-ops. Keep it that way — re-introducing a second
class identity was the source of three separate bugs.

## Plans & issue work

`.agent/plans/README.md` indexes implementation plans for the open issues
and PRs (bugs, roof types, fill types, GIS batch, ...), with milestone
grouping. Read the relevant plan before starting issue work; update its
Status when done. Repo issues/PRs: https://github.com/ranjian0/building_tools

## Git notes

- `.agent/out/` is gitignored (transient session state, screenshots, logs);
  `.agent/tools/` and `.agent/plans/` are tracked.
- Releases: tag `vX.Y.Z` → GitHub Actions builds the zip via
  `scripts/make-release.py` (requires full git history — it walks tags).

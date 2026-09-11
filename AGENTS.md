# AGENTS.md

Guide for AI coding agents working on **Building Tools** — a Blender addon
(Python) for fast building modeling. Read this before making changes.

## Project layout

```
__init__.py            addon entry point (bl_info, panels, version)
btools/                addon package
  building/<feature>/  one dir per feature: *_props.py, *_ops.py, *_types.py
  api/                 scriptable control surface (result/core/options/validate)
  utils/               shared helpers (bmesh, geometry, materialgroup wiring)
  road/                road tool (legacy layout)
tests/                 headless test suite (runs inside Blender)
scripts/               release zip + dev-install scripts
.agent/tools/          Blender session toolkit (`bt` CLI) — see its README.md
.agent/plans/          implementation plans for open issues/PRs
docs/                  Jekyll site (artist docs)
```

- The addon runs **inside Blender**; dev tooling runs outside it.
- `bl_info` (root `__init__.py`) governs the Blender version range; the
  `pyproject.toml` `requires-python` only constrains dev tooling.
- Current dev target: Blender 5.1 at `/home/ranjian0/tools/blender-5.1.2-linux-x64/blender`
  (override with `BT_BLENDER`), Python 3.13 in-session.

## Environment & commands

`uv` manages the venv/lockfile; `just` is the task runner.

| Command | Purpose |
|---------|---------|
| `just test` | headless Blender test suite — **run after every change** |
| `just check` | mypy |
| `just lint` | ruff |
| `just format` | black |
| `just sync` | (re)create the venv from the lockfile |
| `just build` / `just build-dev` | release zip from tag / latest commit |

The live-session toolkit lives in `.agent/tools/`:

```bash
.agent/tools/bt start        # GUI Blender on the 4K monitor
.agent/tools/bt reload       # hot-reload the addon from the working tree
.agent/tools/bt exec demo_building.py
.agent/tools/bt api door --object wall --faces 1 --options '{"fill_type": "PANELS"}'
.agent/tools/bt validate --object wall --expect '{"groups": ["door", "frame"]}'
.agent/tools/bt screenshot demo
.agent/tools/bt stop
```

Full reference: `.agent/tools/README.md` (session protocol, snippets,
Blender 5.1 gotchas).

## Mandatory workflow for any change

1. Make the change.
2. `just format && just check && just lint`
3. `just test` — all tests must pass (46 as of the api work; count drifts).
4. **`bt smoke`** — build all 8 presets + validate matgroup contracts;
   exit 1 on any failure. Run after ANY change to building code.
5. For anything geometry/visual: verify in the live session —

   ```bash
   bt restart && bt reload
   bt scenario multi_storey        # or wall / curved_wall
   bt api <feature> ...            # apply the change
   bt validate --object <name> --expect '{"groups": [...]}'
   bt exec viewport_setup.py && bt screenshot check
   ```

   `bt api`/`bt validate`/`bt scenario` emit JSON + exit codes — branch on
   those, not on prose. Use screenshots only for genuine visual judgment.

## Reference corpus (regression baseline)

`.agent/reference/` holds the committed baseline of what every tool
generates: per case, a JSON log (options, matgroup counts, validation,
`geometry_hash`) + a deterministic iso render. When fixing issues or adding
features, regenerate the affected cases and diff:

```bash
bt reference generate --filter "balcony*"   # subset or full sweep
bt reference diff                            # SEVERE/VISUAL = act; minor = noise
bt reference diff --update                   # promote the new baseline
```

Commit the updated baseline alongside the fix — the reference diff IS the
visual changelog. Known addon flaws are recorded per case in `known_issues`.

## Scriptable api — the only scripted path

**Never drive `bpy.ops.btools.*` from scripts**: Blender resets operator
props to defaults on every scripted call. The supported surface is
`btools/api`:

```python
from btools.api import FloorplanOptions, RoofOptions, FaceTarget, apply_feature
from btools.api.validate import validate_object

r = apply_feature("floorplan", FloorplanOptions(width=10, length=8))
assert r.ok
obj = bpy.data.objects[r.created_object]

r = apply_feature("roof", RoofOptions(type="HIP", height=1.5),
                  FaceTarget(obj, [top_face_index]))
report = validate_object(obj, expect={"groups": ["walls", "roof"]})
```

- Options dataclasses (`btools/api/options.py`) are the single parameter
  format; `None` means "use the operator default".
- Every operation returns `OpResult` (`r.ok`, `r.errors`, `r.matgroup_counts`,
  `r.to_dict()`).
- `validate_object(obj, expect=...)` checks the addon's core contract: every
  face tagged to exactly one material group, plus optional group assertions.
  Geometry seams (door/window frame T-junctions) are common and advisory —
  pass `include_geometry=False` when gating on the contract.

## Adding a feature (conventions)

1. `btools/building/<feature>/` — `*_props.py` (PropertyGroup + `init()`),
   `*_ops.py` (operator; `build(context, prop)` reads edit-mode selection),
   `*_types.py` (pure geometry: `create_*(bm, faces, prop)`).
2. Register in `btools/building/register.py` (order matters) and add the
   panel button in the root `__init__.py`.
3. Tag every generated face with a `MaterialGroup`
   (`add_faces_to_group` / `map_new_faces` decorator). Untagged faces fail
   validation — this is the addon's core contract.
4. Add an options dataclass in `btools/api/options.py`, a runner in
   `btools/api/core.py` (see `_apply_face_feature`), and wire
   `FEATURES`/`OPTION_TYPES`. The drift/round-trip tests
   (`tests/test_api_options.py`) will enforce dataclass↔PropertyGroup parity.
5. Add headless tests under `tests/` and register the module in
   `tests/__main__.py`.

## Blender/Python gotchas (details in .agent/tools/README.md)

- Scripted `bpy.ops` resets operator props each call.
- BMesh element wrappers don't keep their bmesh alive — hold the bmesh in the
  calling frame.
- Fresh `bm.new() + from_mesh()` bmeshes have unset indices (all 0) — call
  `bm.faces.index_update()` before reading `f.index`.
- PropertyGroup getters reading ID-props (arch `parent_height`,
  size_offset `restricted`) raise noisy KeyErrors until `init()` runs — the
  api core calls `init()` before applying options.
- Blender property ids can't start with `_`; pointer-property targets must be
  registered before the groups referencing them.

## Plans & issue work

`.agent/plans/README.md` indexes implementation plans for the open issues and
PRs (bugs, roof types, fill types, GIS batch, ...), with milestone grouping.
Read the relevant plan before starting issue work; update its Status when
done. Repo issues/PRs: https://github.com/ranjian0/building_tools

## Git notes

- `.agent/out/` is gitignored (transient session state, screenshots, logs);
  `.agent/tools/` and `.agent/plans/` are tracked.
- Releases: tag `vX.Y.Z` → GitHub Actions builds the zip via
  `scripts/make-release.py` (requires full git history — it walks tags).

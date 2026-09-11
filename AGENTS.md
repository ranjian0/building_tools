# AGENTS.md

Guide for AI coding agents working on **Building Tools** — a Blender addon
(Python) for fast building modeling. Read this before making changes.

## Project layout

```
__init__.py            addon entry point (bl_info, panels, presets panel, version)
btools/                addon package
  api/                 scriptable control surface (the ONLY scripted path)
    core.py            FaceTarget, feature runners, _edit_session, options_from_dict
    options.py         typed dataclasses per feature (drift-tested vs props)
    presets.py         BuildingPreset/FacadeRule schema + 8 bundled presets
    result.py          OpResult dataclass (status, matgroup_counts, errors)
    select.py          world-space face selectors (storey bands, group filters)
    validate.py        matgroup/geometry/normal reports, validate_object()
  building/<feature>/  one dir per feature: *_props.py, *_ops.py, *_types.py
    materialgroup.py   MaterialGroup enum, face-int-layer tagging, restore pass
    default_materials.py  BT_ PBR node materials per matgroup
    frame.py           shared frame-depth + sill/threshold helpers
    generator.py       legacy random building generator (ops-based, not api)
  utils/               shared helpers (bmesh, geometry, materialgroup wiring)
  road/                road tool (legacy layout)
tests/                 headless test suite (46 tests; runs via bpy module)
scripts/               release zip + dev-install scripts
.agent/tools/          Blender session toolkit (`bt` CLI) — see its README.md
.agent/plans/          implementation plans for open issues/PRs
.agent/reference/      golden corpus (JSON + 1280×1280 4-view composites)
docs/                  Jekyll site (artist docs)
```

- The addon runs **inside Blender**; dev tooling runs outside it.
- `bl_info` (root `__init__.py`) governs the Blender version range; the
  `pyproject.toml` `requires-python` only constrains dev tooling.
- Current dev target: Blender 5.1 at `/home/ranjian0/tools/blender-5.1.2-linux-x64/blender`
  (override with `BT_BLENDER`), Python 3.13 in-session and in the venv.

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
.agent/tools/bt smoke        # build all 8 presets + validate — MANDATORY after building-code changes
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

### Import namespace (critical for tests)

The addon is loaded under TWO names depending on context:
- `building_tools` — via LoadModule in the test harness, or via bt reload
- `btools` — via `sys.path` (repo root on path, plain package import)

**Always use the namespace that matches your context.** In the just-test
harness, `import btools.api.presets` works (the harness registers via
LoadModule's `__main__` quirk). In bt sessions, use
`building_tools.btools.api.presets`. Mixing namespaces creates duplicate
PropertyGroup copies that break pointer-property resolution.

## Building presets

8 presets (suburban house, townhouse, apartment block, modern villa,
mediterranean villa, corner shop, warehouse, office block) defined in
`btools/api/presets.py`. Each composes floorplan + floors + roof + facade
rules via the api. `build_preset(preset, floors, width_scale, depth_scale,
assign_materials)` returns an OpResult with the created object.

- Facade rules target world-space face selectors (see `btools/api/select.py`)
  per storey; the api core handles mode transitions, index resolution, and
  normal normalization.
- `apply_default_materials(obj)` assigns BT_ PBR materials per matgroup;
  called automatically when `assign_materials=True` (the default).
- Preset thumbnails are rendered by `bt thumbs` into `btools/presets/thumbs/`.
- Known addon flaws are documented per case in the reference corpus
  (`multigroup_arch_broken`, `zero_width_window_fill`, etc.).

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

### API runner pattern (for new features)

New features should follow the `_apply_face_feature` pattern in
`btools/api/core.py`:

1. `_edit_session(target)` — enters edit mode, resolves faces by index,
   sets selection flags (operator precondition), yields (bm, faces)
2. Validate faces (bool or list per feature convention)
3. `_prop_instance(prop_cls, "bt_api_<feature>")` — attach prop to scene
4. `prop.init((w, h))` BEFORE `_options_into_prop(prop, options)` —
   init sets ID-props (parent_height, restricted, etc.) that getters need
5. `_target_context(obj)` — routes `bpy.context.object` to the target
6. `create_fn(bm, valid, prop)` — call the geometry function
7. `nulfaces → WALLS` — untagged faces default to WALLS
8. `_normalize_normals(bm)` — recalc + signed-volume flip (see gotchas)

The `_edit_session` finally block normalizes normals, flushes edit mesh,
and returns to object mode.

## Blender/Python gotchas (details in .agent/tools/README.md)

### Mesh/normals
- **Normal inversion**: the floor op's per-face Z-flip hack leaves the
  whole solid consistently INVERTED. `recalc_face_normals` only makes
  normals consistent — it does NOT flip an inverted solid. Use
  `_normalize_normals` in api/core.py (recalc + signed-volume flip).
- **BMesh element wrappers don't keep their bmesh alive** — hold the bmesh
  in the calling frame.
- **Fresh `bm.new() + from_mesh()` bmeshes have unset indices (all 0)** —
  call `bm.faces.index_update()` before reading `f.index`.

### Ops / properties
- **Scripted `bpy.ops` resets operator props each call** — use the api
  or the `build(context, prop)` pattern with scene-attached prop groups.
- PropertyGroup getters reading ID-props (arch `parent_height`,
  size_offset `restricted`) raise noisy KeyErrors until `init()` runs — the
  api core calls `init()` before applying options.
- Blender property ids can't start with `_`; pointer-property targets must
  be registered before the groups referencing them.
- `bpy.utils.previews` is a lazy submodule — `import bpy.utils.previews`
  explicitly or `hasattr(bpy.utils, 'previews')` returns False.

### Environment
- **Stale installed addon**: `import building_tools` in headless scripts
  resolves to `~/.config/blender/5.1/scripts/addons/building_tools/` (from
  a previous `just dev`), NOT the working tree. Use `btools.*` imports with
  `register_building()` for headless scripts, or ensure `bt reload` loaded
  the current code.
- `bpy.ops.uv.cube_project` and other UV ops crash headless — guard with
  `bpy.app.background`.
- `popup_message` crashes headless — `popup_message` already guards with
  `bpy.app.background`.
- The api core's `_edit_session` sets `bpy.app.background`-safe defaults:
  no UV ops, no popups, no window-dependent calls.

### Material groups
- The face int layer `.bt_material_group_index` must exist BEFORE the edit
  bmesh is created (values propagate to the bmesh layers).
- Untagged faces carry -1 (the sentinel written by
  `verify_matgroup_attribute_for_object`). `find_faces_without_matgroup`
  re-tags them to WALLS.
- `_base_nodes` in default_materials.py returns just the bsdf node (not a
  tuple) — the tuple was a bug that crashed every PBR material creation.

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

# Building Tools — Blender Session Toolkit

Persistent Blender session for validating addon changes: hot-reload the addon,
run investigation scripts against the live session, and capture screenshots
for visual analysis. All commands work from the CLI (and thus from an agent).

Blender is launched as a GUI window on the **4K monitor** (auto-detected via
xrandr; override with `--geometry WxH+X+Y`).

## Quickstart

```bash
.agent/tools/bt start              # GUI session on the 4K monitor
.agent/tools/bt reload             # load/hot-reload the addon from this repo
.agent/tools/bt exec demo_building.py           # build a full demo building
.agent/tools/bt exec mesh_report.py             # matgroups + geometry checks
.agent/tools/bt screenshot demo1   # out/screenshots/demo1.png
.agent/tools/bt stop
```

## Commands

| Command | Purpose |
|---------|---------|
| `bt start [--bg] [--factory] [--geometry G]` | Start session (GUI on 4K by default; `--bg` headless) |
| `bt stop` / `bt restart` / `bt status` | Session lifecycle; `status` prints blender/python versions |
| `bt reload` | Hot-reload the addon **from the repo** into the session (no zip/install step) |
| `bt exec <file\|snippet\|- \| -c CODE>` | Run python in the session; exit code + traceback propagate |
| `bt exec <file> --profile` | Also reports wall time |
| `bt eval "expr"` | Evaluate an expression, print its repr |
| `bt api <feature> [--options JSON] [--object N] [--faces i,j] [--json]` | Run a building feature via the scriptable api; JSON result, exit 1 on failure |
| `bt validate [--object N] [--expect JSON]` | Structured validation (matgroups/geometry/normals); exit 1 if invalid |
| `bt scenario <name> [--json]` | Build a reusable test scenario (`wall`, `curved_wall`, `floorplan`, `floors_only`, `multi_storey`); prints face-map JSON |
| `bt reference generate [--filter G] [--out D]` | Run the full reference corpus sweep (JSON log + deterministic render per case) |
| `bt reference diff [--update] [--filter G]` | Regenerate + compare vs committed baseline; SEVERE/VISUAL/minor classification, exit 1 on severe/visual |
| `bt screenshot [name]` | Save `out/screenshots/<name>.png` of the Blender window |
| `bt log [-n N] [-f]` | Show/tail the Blender stdout log |

`bt exec` accepts snippet bare names (e.g. `demo_building.py`) from
`snippets/`, absolute paths, `-` for stdin, or `-c 'code'`. Failed scripts
print the traceback and exit non-zero.

## Reference corpus (`.agent/reference/`)

Golden baseline of what every tool generates: per case, `result.json`
(inputs, step results, matgroup counts, validation report, `geometry_hash`,
environment) + a deterministic 1280x800 workbench render from a canonical
iso camera. Browsed via `index.md`.

```bash
bt start --factory && bt reload          # factory session for reproducible theme
bt reference generate                    # regenerate everything (~2 min)
bt reference diff                        # compare vs committed baseline
bt reference diff --update               # promote the new run to baseline
bt reference generate --filter "balcony*"  # subset
```

Diff severity: **SEVERE** = contract change (validation ok/problems, step
status/errors, added/removed case); **VISUAL** = >0.5% pixels changed;
**minor** = geometry nondeterminism (bmesh iteration order varies per
session, so door/arch frame geometry wiggles by a few faces — advisory
only, does not fail the diff). Known addon flaws are recorded per case in
`known_issues` (e.g. `multigroup-fills` zero-width window division,
`balcony-inner-curved` grouped-curved platform).

### Face selectors

Steps reference faces by selector name, resolved live per step by
`lib/face_select.py` (world-space semantics: canonical front = **-Y**, the
side the render camera sees; candidates ordered by area, largest first):

| Selector | Matches |
|----------|---------|
| `front_wall` / `front_walls` | vertical, -Y-facing, area > 1 |
| `ground_front_wall`(s) | front + median z < 3 |
| `upper_front_wall`(s) | front + 3 < z < top |
| `ground_wall`(s) / `upper_wall`(s) | any side, by height band |
| `top_face` | largest upward face at max z |
| `inner` | curved-wall faces whose normals point at the arc center |
| `all` | everything |

Renders color faces by material group (workbench MATERIAL mode via
`diffuse_color`): walls gray, slabs darker gray, roof/roof_hangs red-brown,
door brown, frame near-black, window blues, balcony ochre, stairs tan —
**untagged faces render bright red**, which makes contract violations
visible at a glance.

### Expectations (matgroup contract)

Every feature case carries `expect: {"groups": [...]}` — the matgroups the
feature must produce. A missing/empty expected group marks the case
`contract violated` in the index; violations are **expected states** for
cases with matching `known_issues` markers (they document current addon
tagging gaps, e.g. `balcony_railing_untagged`), and the diff flags any
*change* in them. Current known violations: the 4 `balcony-*` cases
(railings never tagged).

## Agent loop (typical)

```bash
bt restart && bt reload
bt scenario multi_storey            # -> {"object": "building_001", "faces": {...}}
bt api door --object building_001 --faces 2,3 --options '{"fill_type": "PANELS"}'
bt validate --object building_001 --expect '{"groups": ["door", "frame"]}'
bt exec viewport_setup.py && bt screenshot after-door
```

Everything from `bt api`/`bt validate`/`bt scenario` emits JSON on the last
line and uses exit codes, so results are machine-checkable without parsing
prose. Screenshots are for when visual confirmation is genuinely needed.

## Snippets (`snippets/`)

| Snippet | What it does |
|---------|--------------|
| `demo_building.py` | End-to-end api demo: floorplan (10x8) → 3 floors → hip roof → door → window → structured validation |
| `mesh_report.py` | Active object: per-material-group face table, untagged-face detection, non-manifold edges, loose/zero-area geometry |
| `viewport_setup.py` | Frame all objects, solid shading (consistent screenshots) |
| `face_orientation.py` | Toggle face-orientation overlay (blue=front, red=inverted; for #229-style bugs). `DISABLE=1` env turns it off |
| `scenarios/*.py` | Scenario fixtures used by `bt scenario`: `wall`, `multi_storey`, `curved_wall` — print object name + face-map JSON |

## How it works

`bt start` launches Blender with `lib/driver.py`, which registers a persistent
`bpy.app.timers` loop polling `out/session/` for `req-<id>` marker files. Each
`bt exec`/`eval` writes `cmd-<id>.py` + `req-<id>`; the driver execs the code
(capturing stdout/stderr/tracebacks) and writes `resp-<id>`. The addon is
loaded directly from the repo as the `building_tools` module (importlib spec
with `submodule_search_locations`), so `bt reload` always reflects the current
working tree — no install step.

## Gotchas learned the hard way (Blender 5.1)

1. **Scripted `bpy.ops` calls reset operator props to defaults** every call —
   mutating `wm.operator_properties_last(...)` has no effect on the next
   scripted invocation. Use the scriptable api (`btools.api`, see
   `.agent/plans/api-control-surface.md`) instead of operators.
2. **BMesh element wrappers don't keep their bmesh alive** — a `BMFace`
   obtained inside a helper function dies when the helper's `bm` local goes
   out of scope. Keep the bmesh referenced in the calling frame.
3. **Fresh `bm.new() + from_mesh()` bmeshes have unset face indices (all 0)** —
   call `bm.faces.index_update()` before reading `f.index`.
4. `btools.add_floorplan` polls for **OBJECT** mode (it creates a new object);
   the other building ops poll for `EDIT_MESH`.
5. Blender property ids can't start with `_`, and `PointerProperty` targets
   must be registered before the groups referencing them.
6. Property-groups whose getters read ID-props (arch `parent_height`,
   size_offset `restricted`) raise noisy KeyErrors until their `init()` runs —
   the api core calls `init()` before applying options for exactly this reason.

## Files

```
bt                  CLI entry point (python, stdlib only)
lib/driver.py       Blender-side timer driver
snippets/*.py       Reusable validation scripts
out/session/        Command/response protocol files (transient)
out/screenshots/    Screenshots
out/blender.log     Blender stdout/stderr
```

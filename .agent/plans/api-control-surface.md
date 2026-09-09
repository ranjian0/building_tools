# Plan: Scriptable control surface via `btools/api` (Option A)

**Status**: Done (all phases landed; 42/42 tests, mypy/ruff clean)
**Goal**: Deterministic agent/script operations: explicit inputs
(object + face indices + options dataclass), structured `OpResult` outputs,
no viewport-state coupling. GUI operators stay byte-identical in behavior.

## Research findings (ground truth)

- All 9 feature ops share the shape: `execute` → `props.init(dims)` →
  `build(context, prop)` → `get_edit_mesh()` → selection → `create_*(bm, faces, prop)`.
  The `create_*` type functions are pure-ish; coupling lives in `build()` wrappers.
- Hidden context couplings: `materialgroup.add_faces_to_group` and
  `add_material_group` read `bpy.context.object` (handled via
  `bpy.context.temp_override`); `verify_matgroup_attribute_for_object` takes obj.
- `dict_from_prop` flattens nested prop groups (util_common.py:85) — name
  collisions across groups break the options round-trip.
- Drift: `FloorOptions.slab_outsset` typo (options.py:99).
- `crash_safe` swallows exceptions (no `__wrapped__`), so the api core cannot
  reuse ops `build()` for error capture — runners replicate the small wrapper
  logic and call `create_*`/validate/matgroup helpers directly.
- Scripted `bpy.ops` resets operator props (session-verified) — ops are not a
  scriptable surface; the api is.

## Phases

1. **Decouple from viewport state**
   - `btools/api/result.py`: `OpResult` dataclass (status/feature/object_name/
     created_object/matgroup_counts/errors/warnings, `.to_dict()`).
   - `btools/api/core.py`: `FaceTarget(object, face_indices)`,
     `_prop_instance` context manager (scene-attach pattern), `_edit_session`
     (mode management + faces by index), `_target_context` (temp_override),
     `apply_<feature>` runners for floorplan/floor/roof/door/window/
     multigroup/balcony/stairs/fill. Own try/except → `OpResult(status="error")`
     (no popups). Floorplan runner replicates ops build inline (creates object).
   - `btools/api/api.py` rewritten: thin `create_*` wrappers + `apply_feature`
     dispatcher. Options dataclasses stay the parameter format.
2. **Options single source of truth**
   - Fix `slab_outsset`; add missing `StairsOptions`, `FillOptions`.
   - `dict_from_prop` nested-preserving (generator.py only uses flat groups — safe).
   - `tests/test_api_options.py`: drift test (dataclass fields vs bl_rna props,
     with per-feature ignore lists for mixin aliases) + round-trip test
     (options → prop → dict → compare).
3. **`btools/api/validate.py`**: `matgroup_counts`, `matgroup_report`,
   `geometry_report` (non-manifold/loose/zero-area), `normal_report`
   (flip-seam heuristic), `validate_object(obj, expect)` → JSON-able dict.
4. **`bt` integration**: `bt api <feature> --options JSON [--object N --faces i,j]`,
   `bt validate [--object N] [--json]`, `bt scenario <name>` +
   `snippets/scenarios/{wall,multi_storey,curved_wall}.py` (JSON output with
   object name + face maps).
5. **`demo_building.py`** rewritten on the api (scenario → ops → validate).
6. **Tests/docs**: `tests/test_api.py` headless smoke (floorplan + validate),
   live `bt` smoke, README updates.

## Decisions

- Operators/GUI path unchanged; deep `context.object` refactor of
  `materialgroup.py` deferred (temp_override covers it).
- `create_*` return `OpResult` (old api returned raw objects/None; api was
  never released as stable).
- Options dataclasses are THE parameter format; prop groups remain UI-only.

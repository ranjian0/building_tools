# Plan: Fix "Can't activate in Blender 4.0.2" (#221)

- **Issue**: https://github.com/ranjian0/building_tools/issues/221
- **Type**: Bug
- **Reported**: v1.0.12, Blender 4.0.2 — error on enable:
  `already registered as a subclass "addon updater install popup"`

## Problem

Enabling the addon raises a duplicate-class registration error originating from
the addon-updater UI (`addon updater install popup` is the `bl_idname` of
`AddonUpdaterInstallPopup` from the `blender-addon-updater` `addon_updater_ops` module).

History:

- `addon_updater.py` / `addon_updater_ops.py` were removed in commit `0610b9f`
  ("remove addon updater") and that removal is contained in `v1.0.11`+.
- `__init__.py:150-155` still contains a dead import guarded by `try/except ImportError`.
- Users hit the error when an **older installed copy** (or a stale module left
  registered from the same session after an upgrade/overwrite install) still has
  the updater classes registered; registering the new copy then collides on
  `bl_idname`.

## Current Code State

- `__init__.py:150-169` — `register()` calls `addon_updater_ops.register(bl_info)`
  inside a `try/except ImportError`, then `register_building()` and `register_ui()`.
  No class registration anywhere is guarded against double registration.
- `btools/api/api.py:15-19` — shows the project's existing pattern for tolerating
  "already registered" (`register_property` catches `ValueError`).
- `scripts/make-release.py` — packages `btools/`, `__init__.py`, `LICENSE`,
  `README.md`, `CHANGELOG.md` (no updater files in current zips — good).

## Implementation Steps

1. **Remove dead updater code** from `__init__.py`:
   - Delete the `try: from . import addon_updater_ops ...` blocks in both
     `register()` and `unregister()` (lines ~150-166).
2. **Make registration idempotent / defensive**:
   - In `register_building()` (`btools/building/register.py:62-67`) and
     `register_ui()` (`__init__.py:148`), wrap class registration to skip
     `ValueError` ("already registered") rather than aborting enablement, or
     detect-and-unregister stale classes first. Follow the existing
     `register_property` pattern in `btools/api/api.py`.
   - Keep property registration (`PointerProperty` on `Scene`/`Object`) guarded
     with `getattr(..., None) is None` checks so re-enabling doesn't fail either.
3. **Self-heal on register**: before registering, loop
   `bpy.types` for `BTOOLS_`/updater classes already registered and unregister
   them (the `__main__` block at `__init__.py:171-178` already has this pattern
   for the script-watcher dev flow — extract it into a helper and reuse).
4. **Release notes / README**: add an upgrade note — "fully remove the old
   version and restart Blender before installing an update" — since a same-name
   module overwrite in one session cannot be fully recovered from.
5. Verify the packaged zip contains no updater remnants:
   `unzip -l building_tools_v*.zip | grep -i updater` (extend
   `scripts/make-release.py` with a guard if needed).

## Acceptance Criteria

- Addon can be enabled, disabled, and re-enabled repeatedly in one Blender
  session without `ValueError`.
- Enable succeeds on a profile that previously had v1.0.10/v1.0.11 installed
  (simulated stale registration).
- No references to `addon_updater_ops` remain in the codebase.

## Test Plan

- Extend `tests/__main__.py` (headless Blender) to call `register()` twice and
  assert no exception; call `unregister()` and assert clean teardown.

## Risks

- Swallowing `ValueError` broadly can mask genuine class-name collisions; limit
  the catch to the specific registration calls and log via `print`.

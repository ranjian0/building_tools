# Plan: Document the three toolbar buttons (#212)

- **Issue**: https://github.com/ranjian0/building_tools/issues/212
- **Type**: Documentation
- **Scope**: Document the un-documented controls in the main panel
  (`__init__.py:45-73`):
  1. **Add Fill** (`btools.add_fill`)
  2. **Add Custom Geometry** (`btools.add_custom` + the custom-object picker)
  3. **Remove Geometry** (`btools.remove_geom` / "clear geometry")

## Where Docs Live

- Artist-facing site: `docs/index.md` (Jekyll, GitHub Pages) — links to the
  GitHub wiki per feature.
- Wiki pages per feature (Floorplan, Floor, Door, Window, Multigroup, Roof,
  Stairs, Balcony) — fill/custom/remove have **no pages**.

## Implementation Steps

1. **Gather ground truth from code** (each plan section below cites the source):
   - Fill: `btools/building/fill/fill_ops.py` (`BTOOLS_OT_add_fill`, poll:
     edit mode), `fill_props.py` (fill types: Panels, Glass Panes, Louver, Bar;
     per-type params).
   - Custom geometry: `btools/building/customobj.py` — scene object picker
     (`btools_custom_object`), size/offset/array count, places copies on
     selected faces (rejects Z-facing faces, line 124-129), transfers
     materials, tags `CUSTOM` matgroup.
   - Remove geometry: `btools/building/removegeom.py` — removes building
     elements by type from the mesh (verify exact UX when writing docs).
2. Write three wiki pages (or extend existing door/window pages with a
   "Fill" section) with:
   - what the button does, required selection (edit-mode face selection),
   - property reference table with screenshots,
   - common failure modes (e.g. custom geometry on floor faces → error popup).
3. Add the missing links in `docs/index.md` feature list, and a short
   "Materials" section pointing at the Material Tools panel.
4. Optionally add inline tooltips (`bl_description`) where the operator
   descriptions are missing/terse, e.g. `BTOOLS_OT_add_fill` docstring.

## Acceptance Criteria

- All buttons visible in the Building Tools panel are covered by docs; the
  issue's three named buttons each have a dedicated section with screenshots.

## Test Plan

- N/A (docs); verify links resolve in the Jekyll build locally
  (`bundle exec jekyll serve` per `docs/Gemfile`).

## Risks

- None. Good first-contribution candidate; screenshots can come from
  contributors in the issue thread.

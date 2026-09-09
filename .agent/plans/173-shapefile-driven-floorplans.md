# Plan: Floors/footprints from shapefile & GIS data (#173)

- **Issue**: https://github.com/ranjian0/building_tools/issues/173
- **Type**: Enhancement
- **Use case**: City planning visualisation — import building footprints with
  attribute data (floor count, floor height, slab height) and drive Building
  Tools parameters from it, for ~1000 buildings at a time. Also: keep a
  footprint at ground level (buildings currently leave a hole at the bottom).

## Relationship to Other Plans

- **Shares the batch engine with #214** — plan `214-batch-generation.md` is
  the prerequisite; this plan covers the GIS/shapefile-specific side.
- Randomization of parameters can layer on via `163-randomization-options.md`.

## Current State

- No shapefile parsing anywhere; import path is BlenderGIS (external addon)
  which lands footprints as mesh objects with attributes in **custom
  properties** — the same representation #214 targets.
- Ground footprint preservation: floorplan `build` (`floorplan_ops.py:45-67`)
  creates a new object from scratch; when users join footprints and add floors,
  the base face is consumed (reported "hole at the bottom").

## Implementation Steps

1. **(Prereq) Land #214 batch operator** with attribute mapping.
2. **Ground footprint retention**: add a `keep_footprint` bool (default True)
   to floor/floorplan operations — before consuming the base face, duplicate it
   into a separate `footprint` object (or n-gon face retained in the building
   mesh, tagged to its own matgroup). Resolves the "hole at the bottom" note.
3. **Attribute schema support**: extend batch mapping defaults to cover the
   fields from the issue: `floor_count_attribute` (`"floors"`),
   `floor_height_attribute` (`"floor_height"`), `slab_height_attribute`
   (`"slab_height"`). Map to `FloorOptions` fields (floor count / height /
   slab thickness exist in `btools/api/options.py::FloorOptions`).
4. **Shapefile side (optional, keep out of core)**: rather than adding pyshp
   as a dependency, document + provide a helper script under `scripts/`
   (`shapefile_to_blender.py`) that imports a .shp via pyshp (external, run
   outside Blender) and writes a `.json` manifest; a tiny Blender-side importer
   converts manifest → footprint objects + custom props, then users run Batch
   Generate. Keeps the addon dependency-free.
5. **Docs**: wiki page "GIS workflow" covering BlenderGIS → attribute naming →
   batch generate; include the issue's example data.

## Acceptance Criteria

- A set of footprints with `floors`/`floor_height` custom props generates
  correct multi-storey buildings; each building keeps a ground-level footprint.
- No new addon dependencies introduced by core code.

## Test Plan

- Headless: create footprints with the documented props → batch generate →
  assert storey count matches prop and footprint object exists afterwards.

## Risks

- GIS attribute naming varies wildly; editable mapping + prefix matching (from
  #214) mitigates.

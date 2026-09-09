# Plan: Gable roof wall face not tagged as wall (#228)

- **Issue**: https://github.com/ranjian0/building_tools/issues/228
- **Type**: Bug
- **Symptom**: After creating a **BOX gable** roof, the triangular gable-end wall
  face is in no material group, so Material Tools → walls → Select misses it and
  it renders unassigned.

## Problem

When a box gable roof is created, the original top wall face is deleted and the
roof hangs are rebuilt. The new faces occupying the old wall-top position (the
vertical triangles at each gable end) are created by `bmesh.ops.contextual_create`
and are never added to a material group.

## Current Code State

`btools/building/roof/roof_types.py:55-106` `create_gable_roof`:

- Line 59: `faces = extrude_and_outset(bm, faces, prop.thickness, prop.outset)` —
  extrudes the selected wall-top faces up by `thickness` and outsets; original
  faces are deleted inside `extrude_and_outset` (line 440).
- Lines 60-63: gathers `link_faces` around the new geometry, **deletes them**,
  then rebuilds with
  `faces = bmesh.ops.contextually_create(bm, geom=validate(all_edges)).get("faces")`.
  These rebuilt faces include the gable-end verticals — **untagged**.
- Line 65-66: only the faces *below* (`bot_faces`) are tagged `ROOF_HANGS`.
- `gable_process_box` (lines 331-352) tags the extruded roof body + sides as
  `ROOF_HANGS`, but the rebuilt end-wall triangles never receive `WALLS`.
- Contrast: the **OPEN** gable path tags its gable wall faces correctly at line 357
  (`add_faces_to_group(bm, roof_faces, MaterialGroup.WALLS)`).

The roof module applies tags via `map_new_faces(MaterialGroup.ROOF)` /
`add_faces_to_group` (`btools/building/materialgroup.py:59-97`); any face created
outside those decorators is silently untagged.

## Implementation Steps

1. In `create_gable_roof`, after the `contextual_create` rebuild (line 63),
   partition the new faces:
   - horizontal/roof-slope faces → they get re-tagged later by
     `gable_process_box`; leave as is.
   - **vertical faces whose normal has `z ≈ 0`** → tag with
     `add_faces_to_group(bm, [...], MaterialGroup.WALLS)`.
2. Sanity-check the same helper for the **hip** roof (`create_hip_roof`, lines
   108-136): `extrude_and_outset` there is wrapped in
   `map_new_faces(MaterialGroup.ROOF_HANGS)` and the original wall faces are
   deleted — confirm wall faces below the outset remain tagged (they should, as
   they are pre-existing). Add the same `z ≈ 0` sweep for any newly created
   verticals if found.
3. Consider a final safety pass inside `create_roof` (`roof_types.py:21-31`):
   after all roof types complete, use `find_faces_without_matgroup`
   (`materialgroup.py:198`) on the roof region and log/warn instead of silently
   leaving untagged faces. (Optional, keeps future geometry work honest.)

## Acceptance Criteria

- Repro from the issue (Blosm footprint → floor → box gable roof → Material
  Tools "walls" → Select) selects both triangular gable-end faces.
- All faces of the resulting mesh belong to some material group.

## Test Plan

- Headless test: rectangular floorplan → floors → box gable roof; assert no face
  lacks a matgroup and count of `WALLS` faces increases by 2 (the gable ends).

## Risks

- Low. Tagging only adds attribute values; no geometry change.

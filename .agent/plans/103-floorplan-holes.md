# Plan: Support floorplans with holes (#103)

- **Issue**: https://github.com/ranjian0/building_tools/issues/103
- **Type**: Enhancement
- **Goal**: Floorplans containing interior holes (courtyards) should support
  floors, slabs, roofs, and downstream features.

## Current State

- Floorplan generation (`btools/building/floorplan/floorplan_types.py`) creates
  simple polygons (rect, circle, composite, H-shaped, random). Users who join a
  mesh with a hole into a floorplan object break downstream.
- Wall creation from floorplan outline: `btools/building/floorplan/floorplan_ops.py:45+`
  `build` extrudes the selected face.
- **Straight skeleton already supports holes**:
  `btools/utils/util_skeleton.py:895` `skeletonize(polygon, holes=None, zero_gradient=False)`.
  Roof code currently passes `[]` (`roof_types.py:90,125`).
- Balcony/door/window selection-based features operate per face and are mostly
  hole-agnostic; the blockers are floors/slabs/roof on holed floorplans.

## Implementation Steps

### Phase 1 — Detect and represent holes

1. In floorplan build (`floorplan_ops.py`), detect interior faces: selected
   face + boundary walk; classify contained n-gons as holes via
   point-in-polygon of hole median against outer boundary (mathutils
   `intersect_point_tri` on triangulated outer, or even-odd ray cast).
2. Store the floorplan's holes on the object as a custom property
   (`btools_holes`: list of vertex-index rings) so later operations (floors,
   roof) can recover them without re-analysis.

### Phase 2 — Floors/slabs on holed plans

3. `btools/building/floor/floor_types.py` (`create_floors`): extrude the outer
   region minus holes — bmesh `inset_region`/face math handles regions with
   inner boundaries natively once the hole face is *connected* (bridge the hole
   to the outer boundary with a zero-width seam or use `bmesh.ops.edgeloop_
   fill` alternatives). Simplest robust approach: treat floor generation as
   "extrude all selected faces" (holes simply remain unselected faces) —
   verify and fix any place that assumes a single face / single boundary
   (`get_top_faces`, `dissolve_faces` usage).
4. Slab generation in `floor_types.py` similarly: keep hole faces unextruded.

### Phase 3 — Roofs on holed plans

5. In `create_hip_roof` / `create_gable_roof` (`roof_types.py:90,125`): pass
   detected hole rings into `skeletonize(points, holes)` (signature already
   supports it; polyskel fork needs a smoke test for hole input — write one).
6. Flat roof: already fine (border inset follows boundary).

### Phase 4 — Generated floorplan types with holes

7. Add a `COURTYARD` composite floorplan type (rect with rect hole, sized by
   props `hole_width/height/offset`) as the first-class way to make a holed plan.

## Acceptance Criteria

- A floorplan with a courtyard hole supports: add floors (walls/slabs), roof
  (hip around both boundaries), and placing doors/windows on interior-facing walls.
- Plans without holes are unaffected (regression test).

## Test Plan

- Headless: build courtyard floorplan → floors → hip roof; assert FINISHED,
  inner boundary edges retained at each floor, roof faces form a ring.

## Risks

- Polyskel-fork hole support is untested territory; if buggy, fall back to
  "roof each ring separately" (ties into #187 multi-face roofs).
- Related/depends on: `202-217-interior-walls.md` (shared hole detection),
  `187-multi-face-roofs.md`.

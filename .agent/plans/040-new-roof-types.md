# Plan: New roof types (#40)

- **Issue**: https://github.com/ranjian0/building_tools/issues/40
- **Type**: Enhancement (tracking issue, **Medium Priority**)
- **Checklist**: Flat ✅, Hip ✅, Gable ✅, ❌ Mansard, ❌ Gambrel,
  ❌ Dutch Hip, ❌ Dutch Gable, ❌ Rectilinear Roofing

## Current State

- `btools/building/roof/roof_types.py:21-31` dispatches `FLAT | GABLE | HIP`.
- Hip/Gable are built on the straight skeleton (`btools/utils/util_skeleton.py`,
  `skeletonize(polygon, holes, zero_gradient)` — adapted from polyskel).
- Key primitives available: `extrude_and_outset` (415), `create_skeleton_verts_and_edges`
  (169), `create_skeleton_faces` (201), `dissolve_lone_verts` (317),
  `gable_process_box/open` (331/355).

## Design Insight

The remaining types are **compositions of existing primitives**:

| Type | Construction | Building blocks |
|------|-------------|-----------------|
| Mansard | Hip on a reduced inset footprint, lower band steep, upper shallow | skeleton at two heights + outset band |
| Gambrel | Gable with broken (two-slope) planes | gable + edge subdivision with two height scales |
| Dutch Hip | Hip with a small gable on the ridge | hip + `gable_process_open`-style cap on the top ridge segment |
| Dutch Gable | Gable with small hip corners | gable + hip caps on 2 corners |
| Rectilinear | Skeleton where vertical faces stay vertical to a height before sloping | skeleton arcs with clamped height (flat-top hip) |

## Implementation Steps

1. **Refactor shared skeleton path** first: extract the common
   "dissolve → sort verts → skeletonize → scale → build edges/faces" sequence
   from `create_hip_roof` (108-136) / `create_gable_roof` (55-106) into one
   function taking a `height_scale_fn(arc)` callback. Mansard/Gambrel/
   Rectilinear only differ in how arcs map to Z.
2. **Mansard**: land PR #230 first (plan `pr230-mansard-roof.md`) as the
   scale-based approximation, then optionally replace with the skeleton-based
   version from (1) for non-convex plans (the PR's inset approach breaks on
   concave footprints).
3. **Gambrel**: gable path with per-edge slope: subdivide each original edge
   into 3 segments (via the existing `join_intersecting_verts_and_edges`
   trick), lower segments use shallow `height_scale`, middle steep. New prop:
   `gambrel_break` (0–0.5, position of slope break).
4. **Dutch Hip / Dutch Gable**: generate hip/gable respectively, then find the
   ridge edge(s) (`edges whose both verts have max height`) and apply the
   opposite type's end treatment (small gable triangle / small hip pyramid).
   New props: `dutch_size` fraction.
5. **Rectilinear (flat-top hip)**: clamp `arc.height` at
   `min(arc.height * height_scale, flat_height)`; cap with a flat top face via
   `contextual_create` on the top ring.
6. Each type: `add_material_group(MaterialGroup.ROOF_HANGS)` at dispatch
   (matching existing types), `map_new_faces(MaterialGroup.ROOF)` for the
   sloped faces (avoid the #228 untagged-face class of bug), props in
   `roof_props.py` with per-type `draw()` block, entries in `btools/api/options.py::RoofOptions`.
7. Update roof icons/UI: the type enum is already a simple list — extend in
   registration order (append only, for scene compatibility).

## Acceptance Criteria

- Each new roof type builds on rectangular, L-shaped, and circular footprints
  without errors; all faces tagged to a material group.
- Existing FLAT/GABLE/HIP outputs byte-identical (no regression from the refactor).

## Test Plan

- Parametrized headless test over all roof types × footprint shapes; assert
  FINISHED, no untagged faces, roof face count > 0.

## Risks

- Skeleton edge cases on concave plans (existing popup warning path in
  `create_skeleton_faces`, lines 246-255, applies to all new types).
- Depends on: `pr230-mansard-roof.md` (mansard), `208-hip-roof-by-angle.md`
  (shares the `height_scale_fn` refactor), `187-multi-face-roofs.md` (multi-face input).

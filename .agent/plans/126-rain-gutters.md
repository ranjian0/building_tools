# Plan: Rain gutters (#126)

- **Issue**: https://github.com/ranjian0/building_tools/issues/126
- **Type**: Enhancement (labeled Low Priority)
- **Request**: Gutter profiles along roof eaves for realism (reference image
  in issue).

## Design

Gutters run along the **bottom edge of roof hangs** (the eaves) for hip/gable
(both already create an outset band tagged `ROOF_HANGS`) and optionally the
flat-roof border.

`RoofProperty` additions:

- `add_gutter: BoolProperty`
- `gutter_size` (width/height of profile), `gutter_profile: [HALF_ROUND, RECTANGULAR, K_PROFILE]`
- `add_downspouts: BoolProperty` + `downspout_corners_only` (v2)

## Implementation Steps

1. Identify eave edges after each roof type builds:
   - hip: bottom perimeter edges of the `ROOF_HANGS` band (edges shared with
     the wall / lowest z ring),
   - gable: same, **excluding rake edges** (the sloped gable ends) for BOX
     type — v1: full perimeter is acceptable, an `eaves_only` bool can come later,
   - flat: inner border ring when `add_border`.
   Add a helper `collect_eave_edges(bm, faces)` in `roof_types.py` keyed on the
   matgroup attribute (find `ROOF_HANGS` faces' lowest edges) so it works
   regardless of type.
2. Profile generation `create_gutter(bm, edges, prop)`:
   - HALF_ROUND: arc profile (n-segment semicircle, `profile_segments`=6) swept
     along each edge run (chain edges into polylines first, miter at corners
     via bisector frame — reuse the corner-frame helper from plan #226),
   - RECTANGULAR: U-channel via two extrudes,
   - K_PROFILE: v2, combination of the two.
3. Sweep implementation: build the profile in the edge's plane
   (edge tangent × Z), extrude along the run with `bmesh.ops.extrude_edge_only`
   per segment + `bridge_loop_pairs`/`contextual_create` for corner fills.
   For v1 simplicity: straight segments only, mitered corner cubes.
4. Tag gutters `ROOF_HANGS` (painted-metal role) or new `GUTTER` group — start
   with `ROOF_HANGS` for matgroup-enum stability.
5. Downspouts (Phase 2): at convex corners, vertical box from gutter bottom to
   floor z.
6. Integrate: `create_roof` dispatch calls gutter step after each type when
   `prop.add_gutter`; props + draw section; API options update.

## Acceptance Criteria

- Hip roof with gutter: continuous half-round gutter along all four eaves with
  mitred corners; no floating segments on gable rakes (when `eaves_only`).
- Works with raised limits from #187 (large outsets).

## Test Plan

- Headless: hip + gable roofs with each profile → assert gutter face count >
  0, gutter verts' max z ≤ eave z + profile height (no spikes at corners).

## Risks

- Corner mitering on non-orthogonal eaves (curved walls) — v1 falls back to
  overlapping cubes at corners for non-right angles; note in docs.

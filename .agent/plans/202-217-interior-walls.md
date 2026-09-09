# Plan: Interior walls / interiors (#202 + #217)

- **Issues**:
  - https://github.com/ranjian0/building_tools/issues/202 ("make the walls thick so we get an inner house to step into")
  - https://github.com/ranjian0/building_tools/issues/217 ("Interior feature? Especially for game use")
- **Type**: Enhancement (new feature area — P3)
- **Goal**: Generate buildings with inhabitable interiors: double-shell walls
  (thickness), interior partitions, and eventually doors between rooms.

## Current State

- Floorplans are single-shell: floors/walls extrude one face outward
  (`floorplan_ops.py:45-67`, `floor_types.py`).
- The straight-skeleton library (`btools/utils/util_skeleton.py`) already
  computes interior offset curves — the natural engine for inner shells and
  room partitioning (skeleton arcs are exactly the "last meeting" lines used
  for partition walls in academic roof/partition generation).
- Hole support (#103, plan `103-floorplan-holes.md`) shares detection logic.

## Phased Design

### Phase 1 — Wall thickness (double shell)

1. Floorplan props: `wall_thickness` FloatProperty (default 0 → current
   single-face behavior), placed in `floorplan_props.py`.
2. On floor generation, after extruding the outer shell: compute an inward
   offset polygon of the footprint at distance `wall_thickness` (straight
   skeleton at constant height, or `bmesh.ops.inset_region` on the base face
   with `use_even_offset` — simpler and robust for most plans; fall back to
   skeleton for concave self-intersection cases).
3. Connect outer and inner shells with a top ring (slab edge), leaving the
   interior hollow; tag inner faces to `WALLS` group too.
4. Ceiling option per floor: `add_ceiling` bool creating a slab face ring
   closure so upper floors are walkable in games.

### Phase 2 — Interior partitions (rooms)

5. New operator `BTOOLS_OT_add_partitions` (edit mode, on floor base face):
   run `skeletonize(points)` on the footprint, take arcs above a
   `partition_height` threshold, project them as wall segments at
   `wall_thickness` thickness, minus door openings at `partition_door_width`.
6. Tag partitions `WALLS`; skip arcs shorter than a `min_room_size` prop.

### Phase 3 — Interiors usability

7. Interior door/window placement already works via face selection once inner
   walls exist (no change needed — document it).
8. Address the #217 request for "game use": export-friendly geometry notes in
   docs (keep shells manifold, optional ceiling), plus optional `merge_distance`
   cleanup pass.

## Implementation Steps (order)

1. Wall thickness (Phase 1) — biggest visual payoff, moderate risk.
2. Ceiling option.
3. Partitions operator (Phase 2) behind an "Experimental" panel flag.
4. Wiki page "Interiors" documenting the workflow + #103 hole support notes.

## Acceptance Criteria

- Rectangular and L-shaped floorplan with `wall_thickness = 0.2` produces a
  hollow double-shell building; a player camera can be placed inside; door
  openings cut through both shells via normal door placement.
- Default `wall_thickness = 0` output is geometry-identical to current builds.

## Test Plan

- Headless: thickness build → assert two boundary loops per floor; partition
  build on a T-shaped plan → assert ≥ 2 partition wall clusters, all in `WALLS`.

## Risks

- Inset on highly concave/self-intersecting plans (mitigate: skeleton fallback +
  existing "decrease outset" style error popup pattern).
- Scope creep — phases ship independently; #202 is satisfied by Phase 1 alone.

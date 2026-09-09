# Plan: Extra balcony features (#166)

- **Issue**: https://github.com/ranjian0/building_tools/issues/166
- **Type**: Enhancement (labeled **Medium Priority**)
- **Checklist** (from issue):
  - [x] Balcony on adjacent faces (grouped mode — **already implemented**)
  - [ ] Beveled posts and rails
  - [ ] Columns for the corners
  - [ ] Separation walls between adjacent balconies
  - [ ] Balcony depth control like "Frame Depth" for windows/doors
  - [ ] Curved balconies

## Current State

- `btools/building/balcony/balcony_types.py`: grouped mode exists
  (`create_balcony_grouped`, lines 34-51 — the checklist item "adjacent faces"
  was delivered by it).
- Railing props: `btools/building/railing/railing_props.py`
  (`RailProperty` with fills: POSTS / WALL / RAILS; post/rail via
  `railing.py` builders).
- Depth: `prop.depth` already extrudes the platform — the "depth similar to
  Frame Depth" item likely means a *visual depth offset from the wall* control;
  verify with reporter before building (may already be covered by `depth` +
  `depth_offset`).

## Implementation Steps

1. **Columns for corners** (also serves #226): at convex corners of the
   balcony top face, extrude column boxes from platform bottom to slab above
   (props: `has_columns`, `column_width`). Use the corner-frame helper from
   plan `226-corner-elements-non-right-angles.md` so curved balcony groups work.
2. **Beveled posts and rails**: `RailProperty` additions
   `post_bevel` / `rail_bevel` (FloatProperty, default 0) — apply
   `bmesh.ops.bevel` to post/rail boxes in `railing.py` builders after
   creation. Zero default keeps output identical.
3. **Separation walls**: for grouped balconies, when `prop.has_railing` fill
   is WALL and the group contains an interior (concave) boundary, the wall
   builder already follows the boundary; the request is for **dividers between
   separately-created adjacent balconies** — detect neighboring `BALCONY`
   matgroup faces sharing a vertical edge and add a divider wall segment
   (prop: `divider_width`). Scope v1: only when balconies were created in the
   same selection group batch.
4. **Depth control**: audit `depth`/`depth_offset` semantics
   (`create_balcony_split`, lines 171-197); if `depth_offset` already provides
   the wall-embedded offset, close the checklist item as "already exists" with
   docs; otherwise add `wall_embed` prop.
5. **Curved balconies**: true curved platforms = extrude along a curved face
   group — the grouped path partially does this via inset_region; full support
   (radial railing following an arc) is the hard part. Defer to its own
   follow-up issue; note dependency on #226 corner/bisector utilities.

## Acceptance Criteria

- Items 2–4 shippable independently behind default-off props; grouped curved
  balcony + columns works after #226 lands.
- Checklist in issue updated; curved item split into follow-up issue.

## Test Plan

- Headless: grouped balcony on L-shaped selection with columns + bevel →
  assert column count = 1 (one convex corner), bevel affects post face count.

## Risks

- Divider detection heuristic may misfire on user-edited meshes — v1 restricts
  to same-batch groups (safe).

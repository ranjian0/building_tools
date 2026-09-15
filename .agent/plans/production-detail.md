# Plan: Production-Detail Upgrade — geometry, materials, presets

**Branch**: `feature/production-detail`
**Goal**: Raise generated elements and presets to production asset quality:
correct real-world dimensions, geometric edge/relief detail, PBR materials,
and production export — for both archviz renders and game-engine workflows.

## Research basis

- Full addon audit: flat co-planar frames with `frame_depth` default 0.0
  (no reveal), single-face opaque glass, no sills/thresholds/hardware,
  4-sided "cylinders" for railing members, plain-box columns, no bevel
  utility anywhere, flat diffuse-only materials, hardcoded cube UV 0.5,
  walls with zero thickness, epsilon + global remove_doubles hazards.
- Dimension defaults vs industry norms: window frame 100mm (norm 40-70),
  railing height 700mm (norm 900-1100), stairs 200/120 (norm 280/175),
  arch resolution 6 (norm 24+), panel depth min 10mm (norm 3-15 total).
- Benchmarks: bevels = #1 realism feature; openings-with-depth + sills =
  top close-up win; silhouette tier (parapets, gutters, cornices) dominates
  at distance; PBR + triplanar/box mapping is the standard answer for
  procedurally generated geometry; MaterialGroup contract = semantic export
  slots (our existing advantage); fake interiors + per-instance variation
  are the proven ecosystem "wow" features.
- Decisions: target BOTH archviz and game export; real geometric detail
  (no baked shortcuts); fake interiors + export presets in scope.

## Checklist

### Phase 0 — Dimensional correctness (defaults pass) — DONE (c0fe68e)
- [x] door: frame_thickness 0.10→0.06, frame_depth 0→0.05, door_depth 0.05→0.045
- [x] window: frame_thickness 0.10→0.06
- [x] fills: pane_margin 0.10→0.03, bar_width 0.10→0.06, panel_depth min 0.01→0.002 default 0.015
- [x] railing: corner_post_height 0.7→1.0
- [x] stairs: step_width 0.2→0.28, step_height 0.12→0.175
- [x] arch resolution 6→24; circular window resolution 20→32
- [x] roof: thickness 0.1→0.15, outset 0.1→0.25
- [x] floors: floor_height default 2.0→2.7 (props + api options)
- [x] presets: storey heights to residential norms; regen corpus (baseline
      change is expected and IS the changelog); visual sanity check

### Phase 3 — Materials system (before geometry: biggest visual payoff) — DONE (4f7b42c)
- [x] default_materials.py → PBR node materials per group:
      walls stucco (procedural bump), slabs concrete, roof tile/seam,
      door painted wood, frame dark metal, window panes GLASS
      (transmission 1.0, IOR 1.52), railing metal, balcony concrete
- [x] keep flat `diffuse_color` per material (corpus workbench readability)
- [x] object-coordinate mapping node per material (box-mapping basis)
- [x] variation hook: per-object random offset into the mapping (seed)
- [x] reference corpus + thumbs regen; commit

### Phase 1 — Foundation utilities
- [x] util_mesh: `bevel_edges(bm, edges, width, segments)` with clamping
- [x] util_mesh: `set_smooth_shading(bm, faces, angle)` for arcs/cylinders
- [x] util_mesh: `sweep_profile_along_edges(bm, edge_run, profile, normal)`
      (used by gutters/fascia)
- [x] scope `remove_doubles(dist=0.01)` in fill_types down to 0.0001
- [x] gate + commit

### Phase 2 — Opening details — MOSTLY DONE (frame bevels deferred)
- [x] window sill: protruding sill member (75mm projection, 50mm high,
      25mm drip lip) under the bottom frame member
- [x] door threshold: low sill member at the door opening base
- [x] casing option (add_casing): trim ring proud of the wall (60mm wide,
      15mm proud) around door/window; coplanar wall-strip extrusion
      (recessed opening face excluded)
- [x] frame edge bevels — DONE (bevel-after-fill design): bevel runs
      AFTER fill_face so the opening-face reference is never needed;
      `bevel_frame_edges` (util_mesh) re-tags rebuilt faces by dominant
      region group; `_opening_region` (window/door types) collects the
      fill fragments + frame ring via shared edges.
- [x] mullion joinery: vertical bars pass through horizontals (full-depth
      bars, 15mm z-fudge removed)
- [x] door hardware (add_hardware): rose + lever on the leaf, positioned
      from the frame ring extents (latch-side, handle_height above floor);
      BAR_PULL variant for commercial doors
- [x] arch default resolution bump + smooth shading on arcs
- [x] tests: sill/threshold/hardware presence per case; corpus update; commit

### Phase 4 — Silhouette tier — PARTIAL (gutters/chimney props; cornice/columns deferred)
- [x] roof fascia band along the eave (roof_hangs bottom rim)
- [x] gutters (half-round sweep on fascia) + downspouts at corners
      (prop add_gutters, default False; presets opt in)
- [x] gable ridge cap; verge boards on open gables (add_ridge_cap,
      default True; swept profiles along ridge/rake edges, ROOF-tagged)
- [x] flat-roof parapet coping (coping_size chamfer on the ring's top
      edges, applied when add_border)
- [x] gutters rewritten (was a broken stub: invalid 2-vert faces at the
      wall base): edges chained into side runs, oriented outward, hung
      below the eave, gated to eave sides only (gable ends skipped);
      chimney rewritten to sit on the largest slope face
- [x] cornice/string-course on floor slabs (add_cornice + cornice_size;
      stepped molding swept along each slab ring rim via
      sweep_profile_along_edges, axis-bucketed runs oriented outward;
      tagged SLABS; gated off at detail level LOW)
- [x] column base + capital options (add_column_base/add_column_capital
      + column_cap_size/height on plain columns; column_size decouples
      the shaft from slab_outset)
- [x] chimney (#183): masonry stack + cap + flue pot (prop add_chimney)
- [ ] dormers — DEFERRED (roof-intersection complexity; follow-up)
- [x] tests + corpus + commit (cornice/column/bevel/fake-interior tests
      in test_interiors.py + test_api.py)

### Phase 5 — Presets & production workflow — PARTIAL
- [x] geometry validation layer for agents: probe API (measurements,
      exact interpenetration, ASCII elevations), declarative preset
      checks, bt check + smoke gating (apartment-block carries 6 checks,
      all passing)
- [x] apartment-block balcony redesign: balconies applied BEFORE window
      splits (clean ungrouped platforms, array mirrors the window grid
      14m/4=3.5m bays); storey-4 fragment + railing deficit fixed;
      parapet "asymmetry" was a measurement artifact (walls-bbox
      pollution) — probes now anchor on wall planes
- [x] extend declarative checks to the other 7 presets (group_present,
      no_intersection on element pairs, count_per_storey, symmetric_outset
      for the warehouse); all 8 green via bt check/smoke
- [x] door detail fixes found by the sweep: handle positioned from the
      opening edge (was 70mm from the wall plane, rose buried in the
      jamb); hardware/threshold/sill/casing faces now explicitly tagged
      (were falling to the -1 sentinel -> WALLS)
- [x] probe hardening: wall_planes weighted by area (single-face walls
      lost to window-recess planes); counts_per_storey assigns by the
      floor below (nearest-center straddled mid-storey)
- [x] multigroup entry detail: threshold + lever hardware wired into
      create_multigroup_frame (add_hardware prop, default True);
      add_hardware refactored to take frame_thickness/handle_height/
      handle_style directly (usable without DoorProperty)
- [x] preset opt-ins: gutters on suburban/townhouse/mediterranean/
      warehouse; chimney on suburban (flat-roof presets keep parapets)
- [x] Detail level (Low/Medium/High) — Scene.btools_detail_level +
      btools/utils/detail.py flag table; LOW forces silhouette extras
      (gutters/chimney/ridge_cap/cornice) off, HIGH forces casings on;
      wired into create_roof, add_cornice, create_door, create_window
- [ ] cornices on apartment/office presets (feature exists; preset
      opt-in remains)
- [x] shopfront glass on corner shop (glass_fill_window panes on the
      ground multigroup)
- [x] fake interiors: BT_window_fake_interior material (emissive
      curtain/room glow behind semi-transparent glass, camera-ray mixed)
      + apply_fake_interiors(obj, enable) slot swap; the cheap
      night-render fallback next to the real wall_thickness interiors
- [x] export operator: BTOOLS_OT_export_building (glb/fbx, file dialog,
      applied transforms via a temp duplicate so the scene object is
      untouched, semantic BT_<group> slots from the matgroup layer);
      btools/building/export/ + api helpers export_object /
      prepare_export_object / semantic_slot_names
- [ ] tests + corpus + docs (README feature list) + commit

## Deferred / follow-ups
- ~~Wall thickness~~ — DONE via the adopt-first roadmap item 7
  (`wall_thickness` on floors: double-shell inner skin + per-storey
  floors; interiors partitions feature with treemap rooms + skeleton
  core ring; see adopt-first-roadmap.md)
- Dormers (roof intersections)
- Mitred gutter corners (v1 gutters join with elbows)
- LOD generation
- True arches on multigroup (multigroup_arch_broken)

## Remaining work order (2026-09 review)

Ranked by value/effort; implement in this order:
1. **Export operator** (glTF/FBX) — production-workflow capstone;
   matgroups -> semantic material slots is nearly free
2. **Cornice feature** (`add_cornice`) — slab-line sweep reusing the
   gutter/ridge-cap machinery; unblocks the apartment/office re-tune
3. **Detail level (Low/Med/High)** — cross-cutting gate; lands after
   cornice so it has something to gate
4. **Frame bevels** — bevel-after-fill + re-tag design (unblocks the
   existing add_bevel props)
5. Polish: column base/capital, shopfront glass on corner shop,
   fake-interiors emissive material

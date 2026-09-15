# Adopt-First Roadmap — Implementation Plan

Detailed implementation plan for the adopt-first list from
`research-building-algorithms.md` (the deep-research reference). Every item is
grounded in the current codebase (file:line refs at commit `9135011`) and
extends — rather than duplicates — the existing per-issue plans
(`163-randomization-options.md`, `208-hip-roof-by-angle.md`,
`040-new-roof-types.md`, `pr230-mansard-roof.md`, `202-217-interior-walls.md`,
`214-batch-generation.md`, `173-shapefile-driven-floorplans.md`).

## Conventions every item must follow (from AGENTS.md)

1. Feature layout: `btools/building/<feature>/{*_props,*_ops,*_types}.py`;
   register in `btools/building/register.py` (order matters); panel button in
   root `__init__.py`.
2. Every generated face tagged to a `MaterialGroup` — untagged faces fail
   `validate_object` (the addon's core contract).
3. Options dataclass in `btools/api/options.py` + runner in
   `btools/api/core.py` (`_apply_face_feature` pattern); the drift/round-trip
   tests (`tests/test_api_options.py`) enforce dataclass↔PropertyGroup parity
   automatically — add fields to BOTH or tests fail.
4. Headless tests under `tests/`, registered in `tests/__main__.py`.
5. After every change: `just format && just check && just lint`, `just test`,
   `bt smoke`; for geometry/visual work also `bt reference generate --filter`
   + `bt reference diff` (commit updated baseline alongside).

## Dependency graph and milestones

```
M0 (shared infra)      M1 (quick wins)        M2 (skeleton depth)
Item 0a height_fn ──►  Item 1 seedian         Item 0b face tagging ─► Item 4 offsets
  (roof refactor)        (feeds 6,7,8)         (feeds 2b,3b,4)            │
                       Item 2a roof trims                                     ├─► Item 2b mansard
                       (= 208a slope_mode)                                   ├─► Item 3b weighted skel
                                                                              └─► Item 7 Phase 1 walls
M3 (robustness)        M4 (facades)           M5 (interiors)       M6 (GIS/batch)
Item 5 skel hardening  Item 6 facade DSL      Item 7 interiors     Item 8 batch/OSM
(no deps; anytime)     (needs Item 1)         (needs 0b, 4; 1)     (needs 1; benefits 2,3)
```

Suggested landing order (mirrors the v1.1/v1.2+ milestones in the plans
README): **M0 → M1 → M2 → M3 → M4 → M5 → M6**, with M3 slottable anywhere
after M0.

---

## Item 0 (shared infrastructure): skeleton-roof refactor + face tagging

Not on the adopt-first list itself, but three items (2, 3b, 4) build on it.

### 0a. Extract the shared skeleton-roof pipeline (`height_scale_fn`)

**Current state.** `create_gable_roof` (roof_types.py:95-146) and
`create_hip_roof` (148-176) duplicate the sequence: dissolve faces →
`dissolve_lone_verts` (357) → `sort_verts_by_loops` (179, CW winding — the
skeleton requires it) → `skeletonize(points, [])` (130/165) →
`height_scale = prop.height / max(arc.height)` (133/168) →
`create_skeleton_verts_and_edges` (209) → `create_skeleton_faces` (242) →
per-type finisher (`gable_process_open/box` 395/371).

**Design.** One function:

```python
def build_skeleton_roof(bm, faces, prop, height_fn, zero_gradient=False):
    """Shared hip/gable pipeline. height_fn(arc) -> Z-lift for an arc.

    Returns (face, median, original_edges, roof_faces) so type-specific
    finishers can post-process (gable walls, trims, caps).
    """
```

- `height_fn` defaults to the current closure:
  `lambda arc: arc.height * (prop.height / max_height)` — computed once.
- Move the multi-face dissolve/guard logic (`if len(faces) > 1` block at
  116-118) inside; the box-gable preamble (98-106) stays in
  `create_gable_roof` before calling it.
- `create_gable_roof`/`create_hip_roof` become thin wrappers — byte-identical
  output (regression: reference diff on roof-* cases must be clean/no-op).

**Files.** `btools/building/roof/roof_types.py` only.

**Tests.** Existing `just test` + `bt reference diff --filter "roof-*"`
(no-change gate); parametrized roof test from plan 040 lands here.

**Effort.** 1 day.

### 0b. Skeleton arc → original-edge face tagging

**Current state.** `Subtree = namedtuple("Subtree", "source, height, sinks")`
(util_skeleton.py:115) carries no adjacency info. Roof faces are recovered
indirectly via `create_skeleton_faces`' boundary walk (242-297) keyed on
bmesh `original_edges` — workable for roofs, unusable for offsets (Item 4)
and interiors corridors (Item 7) which need face membership *before* meshing.

**Design.** A wavefront vertex always sits between its `edge_left` and
`edge_right` (util_skeleton.py:121-122); the arcs it emits are exactly the
boundary between those two edges' faces. Tag arcs at creation:

1. Give every contour edge a stable integer id (contour index order; holes
   continue the numbering). `LAV.from_polygon` (441) and `SLAV.__init__`
   (268) already create `Segment`s per edge — store the id on the Segment:
   `Segment = namedtuple("Segment", "p v edge_id")` (backward-compatible:
   existing code ignores the third field; equality in `next_event`
   (`edge.edge == self.edge_left`, 156) compares p/v only if we keep ids
   equal on both sides of the pairing — they are the same id by construction,
   so equality still holds).
2. `Subtree` gains `faces: tuple[int, int]` — the `(edge_left.id,
   edge_right.id)` of the vertex whose event created the subtree:
   - `handle_edge_event` (302): `unify` merges `vertex_a`/`vertex_b`; the
     merged vertex's `edge_left`/`edge_right` are the outer face pair.
   - `handle_split_event` (346): `v1 = LAVertex(..., event.vertex.edge_left,
     event.opposite_edge)` — the two subtree arcs born from the split carry
     the respective pairs.
   - Peak events (whole-LAV collapse, 307-312): faces = the two edges of the
     last standing vertex.
3. Sinks already carry which arc they came from implicitly; additionally
   record per-sink the child arc index so a consumer can walk the face tree:
   extend `sinks` to `(point, child_arc_idx)` OR return a parallel
   `sink_arcs` list — prefer a parallel list to keep `sinks` a plain point
   list (roof_types iterates it directly at 223).

**Tests.** `tests/test_utils_skeleton.py`: rectangle → each arc's faces are
the two adjacent contour edges; L-shape → split arc's faces span non-adjacent
edges. Golden: `weights=None`, no behavior change to roofs (reference diff
no-op).

**Effort.** 2-3 days (mostly test construction).

---

## Item 1: Seeded hierarchical RNG — "seedian" (#163)

**Goal.** One root seed per building → reproducible, per-branch re-rollable
randomization; the orchestration layer for Items 6, 7, 8. Supersedes the
module sketch in `163-randomization-options.md` (same design, extended with
decision paths + logging).

**Current state.**
- `btools/building/generator.py` (legacy) uses the global `random` module —
  unseeded, non-reproducible (generator.py:101-143, 249-253).
- No randomization anywhere in the api path; presets are fully deterministic
  dicts (`presets.py:67+`).
- `OpResult` (`btools/api/result.py`) has no decision log.

**Design.**

```python
# btools/utils/randomizer.py
class BToolsRandom:
    """Seeded RNG with hierarchical decision paths (CityEngine 'seedian').

    rng("roof")        -> independent stream; re-rolling roof decisions
                          never perturbs facade draws.
    Decision log accumulates for OpResult/decision-list debugging.
    """
    def __init__(self, seed): ...
    def rng(self, *path) -> random.Random:   # Random(f"{seed}:{'/'.join(path)}")
    def choice / weighted_choice / jitter / chance helpers (per plan 163)
```

Key rule: **every** random draw goes through
`BToolsRandom.rng(component, sub_path)` — never the global module. Derivation
`random.Random("%s:%s" % (seed, "/".join(path)))` (string seeding is stable
across Python versions — verify once in tests; integers via
`hashlib.blake2b` if not).

**Decision list.** `BToolsRandom.log(path, decision, value)` appends
`(path, decision, value)` tuples; surfaced as `OpResult.decisions` (new
optional field — extend `result.py` dataclass + `to_dict()`).

**Integration points (ordered).**

1. `presets.build_preset(preset, ..., seed=None)` (presets.py:585): when
   `seed` is set, rules may declare `random` blocks consumed via
   `rng("facade", rule_index)`. v1: only `FacadeRule` gains
   `seed_variations: dict` (e.g. `{"fill_type": ["BAR", "GLASS_PANES"]}` →
   per-face weighted choice at apply time).
2. Variation seam per plan 163: door/window/multigroup `build()` paths
   already receive a prop dict via `_options_into_prop` (core.py:204-208) —
   mutate options per face *before* that call, so types (pure functions of
   props) never change.
3. Batch engine (Item 8) derives per-object seeds:
   `BToolsRandom("%s:%d" % (batch_seed, obj_index))`.
4. Legacy `generator.py`: migrate `random.*` calls to a `BToolsRandom` held
   on the generator classes (keeps the "random building" feature but makes it
   reproducible; lowest priority).

**API surface.** `build_preset(..., seed=...)`; `BatchOptions.seed` (Item 8);
no operator changes in v1 (randomization knobs are api/preset-level first,
per plan 163's "v1 Python API only").

**Tests.**
- Reproducibility: same seed → identical `geometry_hash` (build twice via
  `build_preset`, compare via `btools.api.probe`).
- Independence: changing seed of stream `"roof"` leaves `"facade"` draws
  identical (unit test on `BToolsRandom`).
- Default off: no seed → byte-identical builds (golden test).

**Validation.** `bt smoke` unchanged (presets default seedless); add one
presets reference case `preset-suburban-house-seeded` documenting the
deterministic variation.

**Risks.** Python `random` string-seed stability (mitigate: blake2b int
seeds); scope creep into per-knob UI (keep api-only v1 per plan 163).

**Effort.** 3-4 days (module + preset/facade integration + tests).

---

## Item 2: Roof styles from one skeleton — Laycock–Day post-processing (#40, PR #230)

**Goal.** Half-hip, Dutch hip/gable, flat-top (rectilinear) and a robust
mansard, derived from the *same* skeleton run that powers hip/gable — the
"which faces reach the ridge" trick (Laycock & Day 2003).

**Current state.**
- `create_roof` dispatch: FLAT | GABLE | HIP only (roof_types.py:31-38).
- `RoofProperty` (roof_props.py:8-12) enum `roof_types` — append-only
  extension (scene compat).
- `RoofOptions` (options.py:219-231) mirrors it.
- PR #230 mansard is inset/scale-based (breaks on concave plans, no matgroup
  tagging — see `pr230-mansard-roof.md` findings 3-5).
- Zero-gradient gable snapping exists (`handle_edge_event`, skeleton
  util_skeleton.py:326-343) — gable ridge flattening precedent.

**Design.** All new types share `build_skeleton_roof` (Item 0a) with a
type-specific `height_fn` + post-trim:

| Type | height_fn / trim | Construction |
|------|------------------|--------------|
| FLAT-TOP ("rectilinear") | `min(arc.height * scale, flat_height)` | clamp + cap top ring with `bmesh.ops.contextual_create` (plan 040 step 5) |
| HALF-HIP | hip skeleton; ridge vertices clamped at `ridge_fraction * max_height`; cap the truncated ridge with a small vertical gable face | same clamp + `gable_process_open`-style end treatment on the cap ring |
| DUTCH HIP | hip run, then re-run skeleton on the ridge segment footprint scaled by `dutch_size` and graft | per plan 040 step 4: find ridge edges (`add_ridge_cap_and_verges` 455-501 already detects ridge edges by max-z — reuse that detection) |
| DUTCH GABLE | gable run, then hip-cap the two gable ends by skeleton on an end rectangle of width `dutch_size` | inverse of the above |
| MANSARD (skeleton-based) | two-tier: lower band = skeleton roof to `lower_height` on the footprint outset by `lower_outset` (Item 4 offsets), upper = second skeleton (or flat) on the inset footprint | replaces PR #230's scale approach for concave plans; PR's props survive |

v1 shipping order: FLAT-TOP + HALF-HIP (pure post-processing, zero new
geometry risk) → MANSARD tiers (needs Item 4) → DUTCH pair (grafting).

**Implementation steps.**

1. Land Item 0a.
2. `roof_props.py`: extend enum (`FLAT_TOP`, `HALF_HIP`, `DUTCH_HIP`,
   `DUTCH_GABLE`, `MANSARD` — appended after HIP), add
   `flat_height`, `ridge_fraction` (0.3-1.0, default 0.75), `dutch_size`
   (0.1-0.5, default 0.25), and for mansard `lower_height`, `lower_pitch`,
   `upper_pitch`. Conditional `draw()` blocks per type (pattern at
   roof_props.py:113-135).
3. `roof_types.py`: new `create_*` functions over `build_skeleton_roof`;
   ridge detection helper extracted from `add_ridge_cap_and_verges`
   (455-480) into `_find_ridge_edges(roof_faces)`.
4. Matgroups: sloped faces `ROOF` (via existing `map_new_faces` on
   `create_skeleton_faces`), trims/vertical gable caps `ROOF_HANGS`,
   flat-top caps `ROOF` — avoiding the #228 untagged class.
5. `options.py::RoofOptions` + `core.py` no change (runner passes prop
   through); drift tests force field parity.
6. `register.py`/`__init__.py`: no new operator (types ride the existing
   roof op).
7. Reference corpus: new cases `roof-flat-top`, `roof-half-hip`,
   `roof-mansard` in `.agent/tools/snippets/reference_cases.py` (follow the
   existing `roof-hip` case shape) with `checks` entries.

**Tests.** Parametrized headless test (plan 040): every type ×
{rectangular, L-shaped, circular} footprint → FINISHED, zero untagged faces,
roof face count > 0; flat-top: cap face exists at `flat_height` and all
slope verts ≤ it; half-hip: ridge-edge count > 0 and clamped verts at
expected z (probe.measure_object storey bands).

**Validation.** `bt smoke` + `bt reference diff --filter "roof-*"`; screenshot
review via `bt scenario multi_storey` + roof applied (AGENTS.md step 5).

**Risks.** Clamp creates near-degenerate cap rings on narrow plans (guard:
skip cap when ring area < epsilon, warn via `popup_message`); grafting
(Dutch) touches boundary-walk edge cases in `create_skeleton_faces` (246-255
already warns on intersections).

**Effort.** 0a + FLAT-TOP + HALF-HIP: ~4 days. MANSARD: +3 days (with Item
4). DUTCH pair: +4 days.

---

## Item 3: Slope-driven roofs — uniform angle first, then per-edge weighted skeleton (#208)

**Goal.** Drive roof shape by pitch angle / percentage instead of absolute
height; then per-edge slopes via a multiplicatively weighted straight
skeleton (Held & Palfrader CAD 2017; CGAL semantics).

### 3a. Uniform slope (no skeleton changes)

Exactly plan `208-hip-roof-by-angle.md`; restated against current code:

1. `roof_props.py`: `slope_mode` enum `[HEIGHT, ANGLE, PERCENTAGE]` (default
   HEIGHT), `slope_angle` (ANGLE subtype, 5-75°, default 35°),
   `slope_percentage` (5-500, default 70).
2. `roof_types.py`: `slope_to_height_scale(prop, max_arc_height)`:
   HEIGHT → `prop.height / max_arc_height` (current, roof_types.py:133/168);
   ANGLE → `tan(radians(slope_angle))`; PERCENTAGE → `slope_percentage /
   100`. This is the `height_fn` argument of Item 0a — the two items land
   together.
3. UI nicety: effective total height displayed next to the angle field.
4. Tests per plan 208: square 10×10 at 45° → apex ≈ 5; 50% → ≈ 2.5; HEIGHT
   mode regression.

**Effort.** 1-2 days (with 0a).

### 3b. Per-edge weighted skeleton

**Design (multiplicative, positive weights only — CGAL-compatible).**

- Signature: `skeletonize(polygon, holes=None, zero_gradient=False,
  weights=None)`; `weights[i]` = speed scale of contour edge `i` (same id
  order as Item 0b). `weights=None` ≡ all `1.0` — **must reproduce current
  output bit-for-bit** (golden test; default path untouched).
- Semantics (CGAL convention): weight `w_i = tan(pitch_i)`; the wavefront of
  edge i moves *inward at horizontal speed `1/w_i`*; a vertex's arrival
  **time equals its roof height**. With all `w = 1`: speed 1, time =
  distance — exactly today's behavior.
- Code changes in `util_skeleton.py`:
  1. `LAVertex.__init__` (118-150): bisector direction `v` solves the 2×2
     system `n_L · v = 1/w_L`, `n_R · v = 1/w_R` where `n_L/n_R` are unit
     *inward* normals of the two edges (derive from `_left_normalized` /
     `_right_normalized` rotated ±90° — winding sign verified by the
     all-ones golden test). Reflex sign logic (143) unchanged.
  2. Event *times* instead of distances: `_point_line_distance(b, edge.edge)`
     (next_event, ~192/216-222) becomes `w_edge * distance`; edge-event
     distances (218-226) use the merged vertex's edge weights. The heap
     (`EventQueue`, 526) already orders by `distance` first — it now carries
     time; tie counter keeps determinism.
  3. `Subtree.height` = time (already is, under unit weights).
  4. Split-event candidate math (167-210): `linvec`/`edvec` bisector uses
     the weighted system too; eligibility crosses unchanged.
- `roof_types.py`: when `prop.slope_mode != HEIGHT` *and* per-edge overrides
  exist, pass weights; vertex Z = `arc.height` directly (no `height_scale`)
  — mirrors CGAL `extrude_skeleton(angles=..., maximum_height=...)`; cap
  via existing `prop.height` as max-height clamp.
- Per-edge input surface: v1 = api-only — `RoofOptions.edge_weights:
  list[float] | None` applied in contour order (front wall first, CW);
  operator UI for edge selection is the deferred stretch in plan 208 (edge
  float layer) — file as follow-up.

**Tests.**
- Golden: `weights=None` and `weights=[1]*n` → identical subtrees to current
  (reuse `tests/test_utils_skeleton.py` fixtures).
- Asymmetric: rectangle 20×10, long edges pitch 30°, short edges 60° →
  ridge endpoints satisfy both plane heights (assert ridge z == w_short ×
  inset on the short side).
- Angle round-trip: uniform `w=tan(35°)` ≈ 3a's uniform height_fn output
  (same Z within epsilon).

**Risks.** Inward-normal sign under our CW winding (mitigated by golden
test); degenerate near-parallel weighted bisectors (d ≈ 0 guard exists at
util_skeleton.py:35); event-time consistency across split events (validate
on L-shape with mixed weights; bpypolyskel-style merge tolerance may be
needed — coordinate with Item 5).

**Effort.** 5-8 days incl. tests.

---

## Item 4: Skeleton-derived mitered offsets module

**Goal.** Exact inward offsets at arbitrary distances from one skeleton run
(Palfrader & Held 2015) — powers mansard tiers (Item 2), wall thickness
(Item 7 Phase 1), setbacks (Item 8). Replaces ad-hoc
`bmesh.ops.inset_region` uses where topology must be predictable.

**Current state.** Offsets exist only as bmesh insets:
`extrude_and_outset` (roof_types.py:504-532) and `gable_process_open`'s
inset (429-431) — per-face, no polygon-level output, no multi-distance
reuse.

**Design.** New `btools/utils/util_offsets.py`:

```python
def offset_polygons(skeleton, weights, distance) -> list[list[Vector]]:
    """Mitered inward offset contour(s) at `distance`.

    Uses Item 0b face tags: for each surviving edge-face (max arc time in
    the face > distance), the offset segment lies on the line offset by
    `distance` (weighted: horizontal inset = distance / w_i), clipped by the
    two boundary bisectors; segments stitch into closed loops along shared
    arcs. Faces that have died (fully collapsed) contribute nothing —
    topology changes (loops splitting) come out naturally.
    """
def offset_face_segments(skeleton, weights, distance) -> dict[edge_id, (Vector, Vector)]
    # lower-level: per-face segment, for stitching custom topology
```

Stitching algorithm: sort each face's segment endpoints on shared arcs
(arc endpoint at parameter `distance` is shared by construction — both
adjacent faces compute the same point on the bisector, so stitching is
exact, no intersection math needed). Chain segments via arc endpoints;
loops close at edge endpoints (offset corners).

**Consumers.**

1. Mansard tier footprints (Item 2 MANSARD): lower band = skeleton on
   footprint; upper = `offset_polygons(lower_skeleton, w, lower_inset)`.
2. Item 7 Phase 1 wall thickness: inner shell = offset at
   `wall_thickness` (fallback to `inset_region` per plan 202 when the
   footprint is simple — keep both paths; skeleton path wins on concave
   self-intersection cases).
3. Item 8 setbacks: buildable envelope = offset at per-edge distances
   (compose with Item 3b weights for per-street setbacks).

**Tests.** Rectangle offsets = expected rectangles; L-shape at distance past
the reflex collapse → two loops; circle-ish contour → segment count = edge
count; offset at max height → degenerate empty (guard).

**Effort.** 4-5 days after 0b.

---

## Item 5: Skeleton robustness — bpypolyskel techniques (#149)

**Status (complete, 2026-09):** the adversarial corpus (stars/apses/
H/rings/40 randoms) is fully green — skeleton consistency 0/54 failing,
offsets 0/51, roofs 0/52 (regression-locked in
`tests/test_roofs.py::TestAdversarialRoofs` and
`tests/test_offsets.py`). Landed across two passes:

1. Structural: 2-LAV collapse records both vertices' face pairs;
   self-arc cleanup (1e-4); consistency checker
   (`_skeleton_problems`) + deterministic jitter-ladder retry with
   ghost-filtered retry outputs and base-point snapping; consecutive
   crossing pairing in offsets.
2. Follow-up: **terminal drain** — when the event queue empties with
   living vertices (apse chains, no-event reflex chains), their
   bisectors' pairwise intersections give the collapse structure
   (bounded to the footprint neighborhood, material-region only);
   drained runs clamp event times to the drain height (approximate max
   inscribed radius) and drop hole-interior sources. Geometric sink
   times in offsets (distance to flanking edge lines — immune to
   merged-birth points and float32 rounding). Hard iteration bound on
   the event loop (zero-progress cycles can otherwise spin forever).

**Goal.** Fix the Felkel-algorithm failure classes behind #149 (hip roof
failure on complex polygons).

**Current state.** Post-refactor `util_skeleton.py` is polyskel + mathutils
(line refs in Item 0b). `roof_types.join_intersecting_verts_and_edges`
(305-329) + `remove_doubles` (353) paper over some failures *after* meshing.
Known upstream mitigation set (bpypolyskel README, GPL-3.0):

1. node-cluster merging (near-coincident skeleton vertices merged with
   tolerance),
2. ghost-edge filtering (spurious edges from failed splits),
3. apse detection → multi-edge events (semicircular protrusions collapsing
   simultaneously),
4. edge-list input signature + right-handed winding.

**LICENSE CONSTRAINT.** bpypolyskel is GPL-3.0; this repo is MIT — **do not
copy code or vendor files**. Reimplement the techniques from the algorithm
descriptions + their wiki (study `btools/building/...` never imports it;
document the derivation in the module docstring like the polyskel
attribution at util_skeleton.py:1).

**Implementation steps.**

1. Reproduce #149: extract the issue's footprint into
   `tests/test_utils_skeleton.py` as a failing-case fixture (assert
   `skeletonize` returns a consistent face-tagged skeleton — Item 0b makes
   consistency checkable: every arc's faces valid, every edge covered).
2. **Node merging** (highest value): in
   `join_intersections_and_get_skeleton_edges` territory but at the
   *skeleton* level — merge `Subtree` sources within epsilon during event
   handling (after `handle_edge_event`/`handle_split_event`, snap new
   sources to existing ones within 1e-4; log as warning). This kills the
   duplicate-vertex class that #149 shows.
3. **Ghost edges**: split events that return `(None, [])` (skeleton
   util_skeleton.py:383-384) can leave dangling candidates — the xleft/
   xright eligibility re-check (365-380) already guards; add a
   post-skeleton validation pass: arcs whose `faces` tags (0b) reference
   dead edges get dropped before meshing.
4. **Apse multi-edge events**: pattern-match contour sequences of collinear
   short edges (detection: consecutive edges with identical
   `_left_normalized` within tolerance) and pre-merge them in
   `normalize_contour` (84-92) before skeletonizing — a preprocessing
   approximation of bpypolyskel's runtime multi-edge event, far cheaper to
   implement.
5. Each fix gated on its fixture turning green + full reference diff
   (roof/preset cases must not regress).

**Tests.** The #149 fixture; a family of adversarial contours (star, apse,
near-collinear chains) asserting: every original edge appears in exactly one
face tag set; no arc has zero length; meshing via the roof path yields
closed faces (probe: zero non-manifold edges).

**Effort.** 4-6 days (fixture hunting included).

---

## Item 6: Facade rule DSL — CGA subset as Python rules

**Status (complete, 2026-09):** v1 landed as `btools/api/facade.py` +
FacadeRule extensions. `bays` (int or "fill" with stretched
`bay_width`), `align` (shared per-face grid cache — wall faces persist
across applies so indices are stable), `where` (bay_index parity/
position conditions), per-bay seeded variations. Uniform grids map onto
the array mechanism (count = grid.count, one edit session); the per-bay
path (where/variations) re-locates the target wall fragment by plane +
containment after each split. Apartment-block migrated to `align`
(geometry-neutral at default scale — verified against the baseline;
door-count delta is documented session noise). Bonus: fixed a latent
`_prop_instance` bug where stale scene ID-property values (e.g.
size_offset.offset) leaked between apply_feature calls. Tests:
`tests/test_facade.py` (bay math, parity, seeded per-bay,
alignment-under-scaling). v2 text DSL deferred.

**Goal.** The facade multiplier: component splits + float/repeat bay splits
over our existing selectors/matgroup contract (Wonka 2003; Müller 2006;
Eger & Mote 2022's rules-as-functions pattern; Schwarz & Müller SA15
course as the blueprint).

**Current state.** `FacadeRule(feature, faces, storeys, options)` +
`BuildingPreset.facade` (presets.py:26-55) already *is* the seed: selectors
resolve via `select.py:47-152` (world-space + storey + group filters),
features apply via `apply_feature`. Repetition today = `ArrayOptions`
(count/spread) inside each feature — no cross-feature bay grid, no float
sizes, no conditionals.

**Design.** Evolve `FacadeRule` in place (v1, declarative — no new DSL
syntax to parse):

```python
@dataclass
class FacadeRule:
    feature: str
    faces: str
    storeys: tuple = ()
    options: dict = field(default_factory=dict)
    # v1 additions:
    bays: int | str = 1          # int count, or "fill" (compute from face width)
    bay_width: float | None = None   # required when bays == "fill"
    align: str | None = None     # optional cross-rule bay alignment key
    where: dict = field(default_factory=dict)  # {"normal": "front", "bay_index": "even", ...}
```

Semantics (implemented in `build_preset`'s facade stage, presets.py:609+):

1. **Bay grid**: for rules with `bays > 1`/"fill", compute per-face bay
   rectangles (face_width / bays, `bay_width` for fill) — pure geometry on
   the selector's face bounds (reuse `calc_face_dimensions`). Each bay
   becomes a synthetic `FaceTarget`-equivalent region passed to the feature
   via `size_offset.size` + `offset` — no geometry code changes: features
   already place by size/offset within a face.
2. **Alignment**: rules sharing an `align` key derive the same bay grid
   (computed once per face from the first rule) — generalizes the
   apartment-block comment (presets.py:199-207) where balcony bays mirror
   window bays manually.
3. **Conditionals**: `where` evaluated per bay/face (bay_index parity,
   z-band via existing storey logic, group membership) — the predicate-
   grammar layer (Smelik 2014) over the semantic matgroup model.
4. **Randomization hook**: `options` values may reference
   `rng("facade", rule_id, bay_index)` via Item 1 when the preset carries a
   seed (e.g. fill_type rotation per bay).
5. Keep everything as plain dataclasses/dicts — the JSON-serializable shape
   already round-trips through `bt api` and the reference corpus.

v2 (follow-up issue, not this roadmap): a text DSL compiler targeting the
same dataclasses (`split(y){3:Ground | {~3:Floor}*}`), per Schwarz & Müller
course notes §"CGA subset".

**Implementation steps.**

1. Bay-grid computation helper in `presets.py` (or new
   `btools/api/facade.py` if presets.py grows past ~900 lines) + unit tests
   on synthetic face bounds.
2. Extend `FacadeRule` + apply loop; migration: existing presets untouched
   (new fields default to old behavior — drift tests updated).
3. Re-express apartment-block's balcony/window pairing via `align` (same
   geometry, less hand-tuned counts — reference diff must be no-op or
   trivially minor).
4. New demo preset or reference case exercising `bays="fill"` + parity
   conditionals + seeded fill rotation.

**Tests.** Bay math unit tests; preset build with bays →
`probe.ascii_elevation` + `bay_alignment` check (existing check kind) green;
seeded rotation reproducibility.

**Effort.** 5-7 days.

---

## Item 7: Interiors stack (#202 / #217)

**Status (complete, 2026-09):** phases 1-3 landed.

- Phase 1 (double shell): `wall_thickness` on FloorProperty/FloorOptions;
  `add_interior_shell` builds the inner skin (exact mitered offset via
  the item-4 machinery) + per-storey walkable floors; the top face stays
  intact for roofs. Api adds it in a dedicated NON-normalizing session.
- Phases 2-3 (partitions): `btools/utils/util_layout.py` -- squarified
  treemaps (Bruls et al. 2000), shared-edge adjacency segments,
  spanning-tree doors (minimum doors preserving reachability); pure
  Python, headless-tested. New `btools/building/interior/` feature
  (props/ops/types, registered, panel button, api runner
  `apply_feature("interior", ...)`, drift-tested as the 10th feature
  pair): TREEMAP mode (room grid + spanning doors, headers above
  openings) and SKELETON mode (core/perimeter ring at min_corridor
  depth -- the level-set offset). Inset keeps partitions off the inner
  skin.
- **Normal-orientation hardening (the deep fix)**: authored interior
  geometry must never pass through a blanket recalc. (1)
  `_normalize_normals` is now component-aware: main shell + closed
  solids recalc + signed-volume flip; small OPEN components keep
  authored winding (protects interiors across ALL later api ops).
  (2) The three blanket `recalc_face_normals(bm.faces)` landmines are
  scoped: sweep_profile_along_edges (ridge caps/gutters/railings) and
  extrude_and_outset now use `recalc_face_normals_component`; verified
  hash-identical on sweep-heavy presets (suburban-house). Full chain
  (shell -> interior -> roof -> partitions) validated: every inner face
  still points at the rooms.

Remaining (follow-ups): window/door cuts through both shells, room
program weights per preset (currently equal areas + room_count).

**Goal.** Thick double-shell walls → skeleton corridors → treemap rooms →
MST doors. Extends the phases in `202-217-interior-walls.md` with the
research-grounded room algorithm (squarified treemaps, Marson & Musse
2010; adjacency MST doors; Honeybee-style skeleton core/perimeter).

**Current state.** Single-shell floorplans (`floorplan_ops.py:45-67`,
`floor_types.py`); skeleton interior-offset capability noted in plan 202;
no room/partition code anywhere.

**Design.** New feature dir `btools/building/interior/`
(props/ops/types + register) + pure-Python layout utils in
`btools/utils/util_layout.py` (testable without Blender):

```python
# util_layout.py
def squarify(bounding_rect, areas) -> list[Rect]           # Bruls et al. 2000
def zone_rooms(rect, program: dict[str, float], rng) -> dict[str, Rect]
    # two-level: zones (social/private/service) then rooms per zone
def adjacency_doors(rooms: dict[str, Rect], required: list[tuple]) -> list[Door]
    # build room adjacency graph (rect touching), spanning tree +
    # required edges; door = midpoint of shared edge segment
```

**Phases (map to plan 202's phases, refined).**

1. **Phase 1 — wall thickness** (unchanged from plan 202):
   `wall_thickness` on FloorplanProperty (default 0 → byte-identical);
   inner shell via Item 4 `offset_polygons` (fallback `inset_region`); slab
   ring closure; `add_ceiling` option. Tag inner faces `WALLS`.
2. **Phase 2 — skeleton core/perimeter**: `skeletonize` on the *inner*
   footprint (Item 0b tags) → corridor arcs = arcs with both adjacent faces
   on opposite perimeter bands and length ≥ `min_corridor`; render as wall
   segments at `wall_thickness`; central cells (faces fully interior at
   depth > corridor margin) become core rooms.
3. **Phase 3 — treemap rooms**: `zone_rooms` over each floor's inner rect
   with a per-preset room program (areas from preset or
   `building:levels`-derived heuristics); partitions at `wall_thickness`;
   `adjacency_doors` places openings (reuse door feature on the partition
   faces — doors already work on any WALLS face).
4. Operator `BTOOLS_OT_add_interior` (edit mode, floor face(s)); props:
   `wall_thickness`, `add_ceiling`, `partition_mode`
   [SKELETON | TREEMAP | BOTH], `room_program` (enum presets:
   apartment/house/office), `min_corridor`, `door_width`.

**Tests.** Phase 1 per plan 202 (two boundary loops, thickness 0 identical);
Phase 2/3: T-shaped plan → ≥ 2 partition clusters; treemap: areas within 5%
of program; doors: every room reachable (flood-fill on room graph);
`probe.group_intersections("walls", "walls")` == 0 across partitions.

**Validation.** Reference cases `interior-walls`, `interior-rooms`;
`screenshot` review inside a cutaway; game-export notes in docs.

**Effort.** Phase 1: 2-3 days (with Item 4). Phases 2-3: 7-10 days.

---

## Item 8: Batch / GIS pipeline (#214 / #173)

**Goal.** Footprint objects + attributes → batch-generated buildings, with
the OSM Simple-3D-Buildings schema as the canonical attribute vocabulary
(research doc §4 mapping table).

**Current state.** Plan `214-batch-generation.md` is the spec (module
`btools/building/batch/`, `BTOOLS_OT_batch_generate`, attribute mapping,
per-object pipeline via `btools/api`); plan `173` adds GIS defaults +
`keep_footprint` + the out-of-core shapefile helper script.

**Refinements from the research (beyond the two plans).**

1. **Attribute schema v1** — adopt OSM tag names as defaults (research
   table): `roof:shape` (30-value vocabulary → roof enum; prefix match,
   unmapped → fallback), `height`, `min_height`, `building:levels` +
   `roof:levels` (3 m/level fallback), `building` (type class → preset
   pick: apartments→apartment-block, house→suburban-house, retail→
   corner-shop ground rules...), `roof:orientation` (along/across →
   gable-ridge axis), `roof:angle`/`roof:height` (→ Item 3 slope props).
   Keep every attribute name user-editable (plan 214 risk note).
2. **Height cascade**: `height` tag → levels×3 m → class prior → block
   median (neighbors of same `building` value) → default; provenance
   recorded per building in the result log.
3. **Roof dispatch**: `roof:shape` families map onto Items 2/3 outputs
   (hipped→HIP, half-hipped→HALF_HIP, mansard→MANSARD, skillion→ shed
   variant of ANGLE mode with opposite-edge weight, pyramidal→HIP on
   near-square, flat→FLAT+parapet); `roof:orientation` overrides ridge
   axis (v1: rotate footprint 90° pre-build; v2: true axis param).
4. **Per-object seeds**: `BToolsRandom(f"{batch_seed}:{obj.name}")` (Item
   1) drives `window_density` sampling and any random fill rotation.
5. **`keep_footprint`** per plan 173 (duplicate base face into a
   `footprint` object before floors consume it).
6. **Scripts helper**: `scripts/shapefile_to_blender.py` (pyshp, run
   outside Blender → JSON manifest) + manifest importer reading into
   footprint objects + custom props — addon stays dependency-free.
7. **CityJSON exporter (stretch, cheap)**: matgroups already are semantic
   surfaces — a `btools/api/export_cityjson.py` walking
   `probe`/matgroup data would be nearly free differentiation; park as
   follow-up unless trivial.

**Tests.** Plan 214's headless batch test (5 mixed footprints → operator →
assert count/roofs/errors); GIS-schema test: footprints with OSM-style
props → expected RoofOptions resolution (pure function
`resolve_attributes(obj_props, mapping) -> BuildPlan` — unit-testable
without Blender); seeded reproducibility across the batch.

**Validation.** New reference family `gis-*` (small synthetic block: 8
footprints, mixed tags) run through `bt reference generate` for regression.

**Effort.** 8-10 days for the core (plans 214+173 + schema); roof-family
completeness tracks Items 2/3.

---

## Item 8: Batch / GIS pipeline (#214 / #173)

**Status (core complete, 2026-09):** `btools/api/batch.py` +
`btools/building/batch/` + `BatchOptions` (11th drift-tested api pair).
`generate_batch(objects, options)` turns flat footprint objects into
complete buildings via the scriptable api (footprint duplicated; source
kept intact per #173). OSM Simple-3D-Buildings attribute vocabulary by
default (roof:shape / height / building:levels / roof:height /
roof:angle), every attribute name user-editable (BlenderGIS exports);
roof families resolve exact -> prefix -> substring with specific keys
first (hipped-and-gabled before hipped; short synonyms gable/hip/
pyramid); unsupported shapes (skillion, onion, dome, ...) degrade to
FLAT with a warning. Storeys: levels -> height // storey -> default.
Roof pitch: roof:angle (degrees, ANGLE mode) over roof:height. Seeded
window pass: draws keyed by face POSITION (indices go stale across
rebuilds) with per-target re-location via the facade locator (every
window re-splits the walls); decisions recorded on
OpResult.decisions -- same seed, same decisions (the window op's strip
geometry itself carries the documented bmesh nondeterminism).
Operator `btools.batch_generate` (object mode, selected meshes,
props-dialog with mapping/fallbacks/windows/dry-run) + panel button.
Non-flat footprints cancel per-object with errors; dry_run reports the
resolved plan without building. Live 8-building mixed block verified
(8/8 built, windows placed, all valid; operator FINISHED).

Remaining (follow-ups): preset-per-building-type selection (apartments
-> apartment-block), roof:orientation ridge axis, block-median height
imputation, CityJSON exporter via the matgroup layer,
scripts/shapefile_to_blender.py helper.

## Consolidated effort / sequencing

| # | Item | Issues | Effort (dev-days) | Depends on | Milestone |
|---|------|--------|-------------------|------------|-----------|
| 0a | skeleton-roof `height_fn` refactor | #40/#208 prereq | 1 | — | M0 |
| 1 | seedian RNG | #163 | 3-4 | — | M1 |
| 3a | slope_mode uniform | #208 | 1-2 | 0a | M1 |
| 2a | FLAT-TOP + HALF-HIP trims | #40 | 3 | 0a | M1 |
| 0b | arc face tagging | (infra) | 2-3 | — | M2 |
| 4 | mitered offsets | (infra) | 4-5 | 0b | M2 |
| 2b | MANSARD + DUTCH pair | #40/PR230 | 7 | 0a, 4 | M2 |
| 3b | weighted skeleton | #208 stretch | 5-8 | 0a (0b helpful) | M2 |
| 5 | skeleton robustness | #149 | 4-6 | 0b (for validation) | M3 |
| 6 | facade DSL v1 | (new capability) | 5-7 | 1 | M4 |
| 7 | interiors | #202/#217 | 10-13 | 4, 1 | M5 |
| 8 | batch/GIS | #214/#173 | 8-10 | 1 (2/3 for roofs) | M6 |

Total ≈ 55-70 dev-days; M0+M1 alone (≈ 1.5 weeks) delivers user-visible
wins (angle-driven roofs, two new roof styles, reproducible randomization
foundation) with minimal risk.

## Global verification protocol (every item)

1. `just format && just check && just lint`
2. `just test` (count grows per item; keep `tests/__main__.py` in sync)
3. `bt smoke` — 8 presets green
4. `bt reference generate --filter <affected> && bt reference diff` — no
   SEVERE/VISUAL; commit baseline updates with the change
5. Geometry items additionally: `bt check --elevation` ASCII review +
   `bt screenshot` on a live scenario (AGENTS.md step 5)

# Plan: Randomization with master decision list (#163)

- **Issue**: https://github.com/ranjian0/building_tools/issues/163
- **Type**: Enhancement (labeled **Low Priority**)
- **Request**: Randomizing options driven by a "master decision list"
  (e.g. gabled for all, rule-based window/door placement); OSM-metadata-driven
  generation (overlaps #214/#173).

## Design

A seeded-RNG variation layer over the existing builders, plus a declarative
"decision list" that biases choices.

### Core: randomization module

`btools/utils/randomizer.py`:

- `BToolsRandom(seed)` — `random.Random` wrapper; all variation flows through
  it so results are reproducible per seed (requirement for batch/testing).
- Helpers: `choice`, `weighted_choice`, `jitter(value, amount)`, `bool(p)`.

### Variation knobs (per component, default off)

| Component | Knob | Effect |
|-----------|------|--------|
| Door/Window/Multigroup | `random_fill` | per-instance fill type from a user-enabled set |
| Door/Window | `jitter_size`, `jitter_offset` | ± fraction of size/offset |
| Roof (batch context) | `random_roof_types` | pick from enabled roof types per building |
| Floors | `jitter_floor_height` | per-floor height variation |
| Balcony | `random_presence` | skip placement with probability p |

1. Implement variation **at selection time** in each op's `build()`: when the
   randomizer is enabled, per split-face, adjust the prop dict passed into the
   type builders (types are pure functions of props — ideal seam; no geometry
   code changes).
2. `RandomProperty` group (seed, enable flags per knob, allowed-value sets)
   shared via pointer from the component props that opt in.

### Master decision list

`btools/building/rules.py` — simple declarative rules applied before builders:

```python
{"component": "window", "if": {"floor": "ground"}, "set": {"fill_type": "BAR"}}
{"component": "roof", "set": {"type": "GABLE"}}   # "gabled for all"
```

1. v1: expose as a Python API only (dicts passed to the batch engine from
   #214); UI rule editor only if demand materializes (file follow-up).
2. Evaluation: rules run once per element in deterministic order; last
   matching rule wins; randomization applies within the rule-chosen sets.

### OSM metadata part

Handled by the attribute mapping in `214-batch-generation.md` — cross-link;
nothing extra here beyond allowing rule conditions on object custom props
(`"if": {"prop": {"Roof Form": "gable"}}`).

## Implementation Steps

1. Randomizer module + tests (pure-python, no Blender needed).
2. Wire `jitter_size/offset` + `random_fill` into door/window first (highest
   visual value).
3. Batch integration: seed + knobs surface in batch props (#214).
4. Rules module + API + docs.

## Acceptance Criteria

- Same seed + same inputs ⇒ identical output building (golden test).
- All knobs default off ⇒ byte-identical geometry to current behavior.

## Test Plan

- Unit-test the randomizer distribution/reproducibility; headless golden
  building test with fixed seed.

## Risks

- Low when confined to the prop-variation seam; avoid touching geometry code.

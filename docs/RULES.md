# Rule files — the btools vocabulary

A rule file is a plain Python file with an optional `build(ctx)` entry
point. The `ctx` object wraps the whole btools api with agent-friendly
shorthands. Run it with:

```bash
btools run house.py --render confirm.png --export house.glb --json
```

Exit code is `0` iff every step succeeded. `--json` prints a machine
summary (objects, statuses, decisions) to stdout.

## The context (`ctx`)

### Building steps

| Call | Purpose |
|------|---------|
| `ctx.floorplan(**opts)` | Flat footprint (`FloorplanOptions`) |
| `ctx.floors(**opts)` | Storeys, slabs, optional double-shell walls (`FloorOptions`; `wall_thickness > 0` enables interiors) |
| `ctx.roof(**opts)` | Roof (`RoofOptions`; types FLAT/GABLE/HIP/FLAT_TOP/MANSARD/HALF_HIP) |
| `ctx.interior(**opts)` | Room partitions (`InteriorOptions`; modes TREEMAP/SKELETON, `inset` keeps walls off the inner skin) |
| `ctx.windows(storeys=None, **opts)` | Windows on wall faces (`WindowOptions`) |
| `ctx.doors(**opts)` | Doors on wall faces (`DoorOptions`) |
| `ctx.preset(id, **kw)` | Build one of the 8 bundled presets (`btools list-presets`) |
| `ctx.feature(name, faces=None, **opts)` | Generic passthrough (`balcony`, `stairs`, `fill`, ...) |

Each step returns an `OpResult` (`.ok`, `.status`, `.errors`,
`.matgroup_counts`, `.decisions`) and is recorded on `ctx.results` /
`ctx.warnings` / `ctx.decisions`.

### Confirmation channels

| Call | Purpose |
|------|---------|
| `ctx.render(path, view="iso")` | Single confirmation PNG |
| `ctx.render(path, views=("front","right","top","iso"))` | Multi-view set (`out.front.png`, ...) |
| `ctx.ascii(view="front")` | Text elevation — readable without vision |
| `ctx.export("house.glb")` | glb/glb/fbx with semantic `BT_<group>` material slots |

### Determinism

`ctx.rng(*path)` hands out seeded random streams. Same seed + same rule
⇒ same building; one re-roll never disturbs the others (hierarchical
sub-seeds). Render engine: EEVEE → Workbench → Cycles-CPU fallback
(EEVEE needs a GPU; the others render anywhere).

## Batch mode

```python
def build(ctx):
    footprints = [...]  # objects with custom props (roof:shape, height, ...)
    results = ctx.batch(footprints, window_density=0.6)
```

Reads the OSM Simple-3D-Buildings attribute vocabulary by default
(`roof:shape`, `height`, `building:levels`, `roof:height`, `roof:angle`);
every attribute name is editable on `BatchOptions`. Unsupported roof
shapes degrade to FLAT with a warning.

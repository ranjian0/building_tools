"""Batch generation from footprint attributes (roadmap item 8; #214/#173).

Each selected flat footprint object becomes a complete building via the
scriptable api (floors + roof + optional seeded window pass), driven by
the object's custom properties. The OSM Simple-3D-Buildings vocabulary
is the canonical schema (roof:shape / height / building:levels /
roof:height / roof:angle); attribute names are user-editable for
BlenderGIS and shapefile exports.

Resolution rules:

- roof type: exact -> prefix -> substring match on the roof:shape value
  (longest keys first, so "hipped-and-gabled" resolves before "hipped");
  unmapped shapes (skillion, dome, onion, ...) degrade to FLAT with a
  warning
- storeys: building:levels -> height // storey_height -> default
- roof pitch: roof:angle (degrees) wins over roof:height (absolute)
- per-building window pass: seeded sub-streams keyed by the source
  object name, so a batch is reproducible and one building can be
  re-rolled without disturbing the others
"""

import math

import bpy

from .core import FaceTarget, apply_feature, options_from_dict
from .options import BatchOptions, FloorOptions, RoofOptions, WindowOptions
from .result import OpResult
from .select import select

# -- specific families first: "hipped-and-gabled"/"half-hipped" must
#    resolve before the plain "hipped" prefix
ROOF_TYPE_MAP: list[tuple[tuple[str, ...], str]] = [
    (
        ("half-hipped", "side_hipped", "side_half_hipped", "hipped-and-gabled"),
        "HALF_HIP",
    ),
    (("gabled_height_moved", "crosspitched", "gabled", "gable", "pitched"), "GABLE"),
    (("pyramidal", "pyramid", "hipped", "hip"), "HIP"),
    (("mansard",), "MANSARD"),
    (("flat",), "FLAT"),
    (("flattop", "flat_top"), "FLAT_TOP"),
]

# -- shapes we cannot represent yet: degrade to FLAT with a warning
ROOF_TYPE_FALLBACKS = (
    "skillion",
    "lean_to",
    "shed",
    "saltbox",
    "sawtooth",
    "butterfly",
    "round",
    "cone",
    "dome",
    "onion",
    "many",
)

_KNOWN_ROOF_TYPES = ("FLAT", "GABLE", "HIP", "FLAT_TOP", "MANSARD", "HALF_HIP")


def resolve_roof_type(value):
    """roof:shape value -> (RoofOptions type, warning or None)."""
    if value is None:
        return None, None
    text = str(value).strip().lower()
    if not text:
        return None, None
    for keys, roof in ROOF_TYPE_MAP:
        for key in keys:
            if text == key or text.startswith(key) or key in text:
                return roof, None
    for key in ROOF_TYPE_FALLBACKS:
        if text == key or text.startswith(key) or key in text:
            return "FLAT", "roof shape %r not supported yet; using flat" % value
    return None, None


def _as_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value):
    f = _as_float(value)
    if f is None or f < 1:
        return None
    return int(f)


def resolve_building_plan(props, options=None):
    """Custom-property dict -> (floor kwargs, roof kwargs, warnings).

    Pure function (no bpy); unit-testable headless."""
    options = options or BatchOptions()
    warnings = []

    def get(name):
        return props.get(name)

    # -- storeys: levels -> height // storey -> default
    levels = _as_int(get(options.levels_attr))
    height = _as_float(get(options.height_attr))
    if levels:
        floor_count = levels
    elif height:
        floor_count = max(1, int(height // options.storey_height))
    else:
        floor_count = options.default_floor_count

    floor_height = _as_float(get(options.floor_height_attr)) or options.storey_height

    # -- roof family
    roof_type, warn = resolve_roof_type(get(options.roof_type_attr))
    if roof_type is None:
        roof_type = options.default_roof_type
    if warn:
        warnings.append(warn)

    # -- roof pitch: angle (degrees) over absolute height
    roof_kwargs = {"type": roof_type, "height": options.default_roof_height}
    roof_angle = _as_float(get(options.roof_angle_attr))
    roof_height = _as_float(get(options.roof_height_attr))
    if roof_angle and 5.0 <= roof_angle <= 75.0:
        roof_kwargs.update(slope_mode="ANGLE", slope_angle=math.radians(roof_angle))
    elif roof_height:
        roof_kwargs["height"] = roof_height

    floor_kwargs = {
        "floor_count": floor_count,
        "floor_height": floor_height,
    }
    return floor_kwargs, roof_kwargs, warnings


def _flat_base_ok(obj, eps=1e-4):
    """All verts within eps of the lowest z (a flat footprint)."""
    zs = [v.co.z for v in obj.data.vertices]
    if not zs:
        return False
    base = min(zs)
    return all(abs(z - base) <= eps for z in zs)


def generate_batch(objects, options=None):
    """Build complete buildings from flat footprint objects.

    Returns one OpResult per source object (feature "batch", created_object
    = the new building). The source footprints are never modified."""
    options = options or BatchOptions()
    results = []

    for src in objects:
        result = OpResult(
            "ok" if not options.dry_run else "skipped", "batch", object_name=src.name
        )
        result.warnings = []

        if src.type != "MESH":
            result.status, result.errors = "cancelled", ["not a mesh"]
            results.append(result)
            continue
        if not _flat_base_ok(src):
            result.status = "cancelled"
            result.errors = ["footprint is not flat (varying vertex z)"]
            results.append(result)
            continue

        props = {k: v for k, v in src.items() if not k.startswith("_")}
        floor_kwargs, roof_kwargs, warns = resolve_building_plan(props, options)
        result.warnings.extend(warns)

        if options.dry_run:
            result.warnings.append(
                "dry run: floors=%(floor_count)d roof=%(type)s"
                % dict(floor_kwargs, **roof_kwargs)
            )
            results.append(result)
            continue

        # -- duplicate the footprint; the original stays intact
        me = src.data.copy()
        new_obj = bpy.data.objects.new(src.name + "_bld", me)
        bpy.context.scene.collection.objects.link(new_obj)

        res = apply_feature(
            "floor", options_from_dict(FloorOptions, floor_kwargs), FaceTarget(new_obj)
        )
        if not res.ok:
            result.status, result.errors = res.status, res.errors
            results.append(result)
            continue

        top = select(new_obj, "top_face")
        if not top:
            result.status, result.errors = "error", ["no top face after floors"]
            results.append(result)
            continue
        res = apply_feature(
            "roof",
            options_from_dict(RoofOptions, roof_kwargs),
            FaceTarget(new_obj, top),
        )
        if not res.ok:
            result.status, result.errors = res.status, res.errors
            results.append(result)
            continue

        # -- optional seeded window pass on the upper storeys
        if options.window_density > 0.0:
            from ..utils.randomizer import BToolsRandom

            rng = BToolsRandom("%s:%s" % (options.seed, src.name))
            floor_count = floor_kwargs["floor_count"]
            fh = floor_kwargs["floor_height"]
            faces = select(
                new_obj,
                "walls",
                floor_height=fh,
                storeys=tuple(range(1, max(2, floor_count))),
            )
            from mathutils import Vector

            from .facade import locate_wall_fragment

            # -- key draws by face position (bmesh iteration order is
            #    not stable across rebuilds) and re-locate each target
            #    before applying: every window re-splits the walls, so
            #    indices gathered upfront go stale
            targets = []
            for face_idx in faces:
                poly = new_obj.data.polygons[face_idx]
                center = (
                    round(poly.center.x, 3),
                    round(poly.center.y, 3),
                    round(poly.center.z, 3),
                )
                normal = Vector((poly.normal.x, poly.normal.y, poly.normal.z))
                targets.append((center, normal))
            # -- deterministic application order (select's index
            #    tiebreak is not stable across rebuilds)
            targets.sort(key=lambda t: t[0])
            for center, normal in targets:
                if not rng.chance(
                    ("window",) + center, min(1.0, options.window_density)
                ):
                    continue
                result.decisions.append(("window/%s" % src.name, "place", center))
                face_idx = locate_wall_fragment(
                    new_obj, Vector((center[0], center[1], center[2])), normal
                )
                if face_idx is None:
                    continue  # face already consumed by an earlier window
                wres = apply_feature(
                    "window",
                    options_from_dict(WindowOptions, {}),
                    FaceTarget(new_obj, [face_idx]),
                )
                if not wres.ok:
                    result.warnings.append(
                        "window at %r failed: %s"
                        % (center, (wres.errors or ["?"])[0].splitlines()[0])
                    )
                else:
                    result.warnings.extend(wres.warnings)

        result.created_object = new_obj.name
        from .validate import matgroup_report

        result.matgroup_counts = matgroup_report(new_obj)["groups"]
        results.append(result)

    return results


def batch_summary(results):
    """One-line human summary of a generate_batch run."""
    ok = sum(1 for r in results if r.ok)
    failed = [r.object_name for r in results if not r.ok]
    text = "batch: %d/%d built" % (ok, len(results))
    if failed:
        text += "; failed: %s" % ", ".join(failed)
    return text

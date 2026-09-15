"""Scriptable API for building feature operations.

Each `create_*` function takes an options dataclass and an optional
FaceTarget (object + face indices) and returns an OpResult with structured
status/matgroup/error information. Operations never depend on viewport
selection; when `target` is omitted for a face feature, the active object
(and its selection, if in edit mode) is used as a convenience fallback.

Example:
    from btools.api import FloorplanOptions, RoofOptions, apply_feature
    res = apply_feature("floorplan", FloorplanOptions(width=10, length=8))
    assert res.ok

Low-level runners live in `core.py`; validation helpers in `validate.py`.
"""

from .batch import (  # noqa: F401 -- re-exported surface
    batch_summary,
    generate_batch,
    resolve_building_plan,
    resolve_roof_type,
)
from .checks import (  # noqa: F401 -- re-exported surface
    CHECK_KINDS,
    run_checks,
)
from .core import (  # noqa: F401 -- re-exported surface
    FEATURES,
    FaceTarget,
    apply_balcony,
    apply_door,
    apply_feature,
    apply_fill,
    apply_floor,
    apply_floorplan,
    apply_multigroup,
    apply_roof,
    apply_stairs,
    apply_window,
    target_from_context,
)
from .options import (
    BalconyOptions,
    DoorOptions,
    FillOptions,
    FloorOptions,
    FloorplanOptions,
    MultigroupOptions,
    RoofOptions,
    StairsOptions,
    WindowOptions,
)
from .probe import (  # noqa: F401 -- re-exported surface
    ascii_elevation,
    border_outsets,
    elevation_bays,
    group_intersections,
    group_protrusions,
    intersection_report,
    measure_object,
    storey_bands,
)


def _feature_fn(feature):

    try:
        return FEATURES[feature]
    except KeyError:
        raise ValueError("unknown feature %r (have: %s)" % (feature, sorted(FEATURES)))


def create_floorplan(options: FloorplanOptions, target=None):
    return _feature_fn("floorplan")(options)


def create_floors(options: FloorOptions, target: FaceTarget | None = None):
    return _feature_fn("floor")(target, options)


def create_roof(options: RoofOptions, target: FaceTarget | None = None):
    return _feature_fn("roof")(target, options)


def create_door(options: DoorOptions, target: FaceTarget | None = None):
    return _feature_fn("door")(target, options)


def create_window(options: WindowOptions, target: FaceTarget | None = None):
    return _feature_fn("window")(target, options)


def create_multigroup(options: MultigroupOptions, target: FaceTarget | None = None):
    return _feature_fn("multigroup")(target, options)


def create_balcony(options: BalconyOptions, target: FaceTarget | None = None):
    return _feature_fn("balcony")(target, options)


def create_stairs(options: StairsOptions, target: FaceTarget | None = None):
    return _feature_fn("stairs")(target, options)


def create_fill(options: FillOptions, target: FaceTarget | None = None):
    return _feature_fn("fill")(target, options)

"""Complete-building presets.

A preset is a declarative recipe composed from the scriptable api:
floorplan massing + storeys + roof + facade rules (features placed on
world-space face selectors, optionally per storey). `build_preset` executes
the recipe and returns a structured OpResult; the facade rules use the same
selectors as the reference tooling (see btools/api/select.py).

Presets give users a complete building to start with; the regular feature
operators remain the editing path afterwards.
"""

from dataclasses import dataclass, field

import bpy

from .core import OPTION_TYPES, FaceTarget, apply_feature, options_from_dict
from .options import FloorOptions, FloorplanOptions, RoofOptions
from .result import OpResult
from .select import select
from .validate import validate_object

# ---------------------------------------------------------------- schema


@dataclass
class FacadeRule:
    """Place a feature on selected faces of the given storeys.

    faces   -- selector name (front_walls, side_walls, back_walls, walls,
               ground_front_wall, all, ...)
    storeys -- storey indices to apply on; empty tuple = every storey
               (ground included)
    options -- feature options (kwargs for the feature's options dataclass);
               array count/spread handles repetition within a face
    """

    feature: str
    faces: str
    storeys: tuple = ()
    options: dict = field(default_factory=dict)


@dataclass
class BuildingPreset:
    id: str
    label: str
    description: str = ""
    reference: str = ""
    floor_height: float = 3.0
    floorplan: dict = field(default_factory=dict)  # FloorplanOptions kwargs
    floors: dict = field(default_factory=dict)  # FloorOptions kwargs
    roof: dict = field(default_factory=dict)  # RoofOptions kwargs
    facade: list = field(default_factory=list)  # list[FacadeRule]
    checks: list = field(default_factory=list)  # declarative geometry checks


# ---------------------------------------------------------------- registry

PRESETS: dict = {}


def _register(preset):
    PRESETS[preset.id] = preset


_suburban = BuildingPreset(
    id="suburban-house",
    label="Suburban House",
    description="Two storey family house, open gable roof, paneled door "
    "and windows on the front.",
    reference="https://commons.wikimedia.org/wiki/File:House_on_suburban_street_in_Sunshine,_Victoria.jpg",
    floorplan={"type": "RECTANGULAR", "width": 8.0, "length": 6.0},
    floors={"floor_count": 2, "floor_height": 3.0, "add_slab": True},
    roof={
        "type": "GABLE",
        "gable_type": "OPEN",
        "height": 1.6,
        "thickness": 0.12,
        "outset": 0.15,
        "add_gutters": True,
        "add_chimney": True,
    },
    facade=[
        FacadeRule(
            "door", "ground_front_wall", (0,), {"size_offset": {"size": [1.2, 2.2]}}
        ),
        FacadeRule(
            "window", "ground_front_walls", (0,), {"size_offset": {"size": [1.2, 1.4]}}
        ),
        FacadeRule(
            "window",
            "front_walls",
            (1,),
            {"array": {"count": 2}, "size_offset": {"size": [1.2, 1.4]}},
        ),
        FacadeRule(
            "window", "side_walls", (0, 1), {"size_offset": {"size": [1.2, 1.4]}}
        ),
    ],
    checks=[
        {"kind": "group_present", "groups": ["walls", "roof", "frame", "window"]},
        # NOTE: walls/frame is exempt -- sills/thresholds are proud trim
        # that crosses jamb edges at the opening seam (T-junction class,
        # advisory per AGENTS.md); element-element pairs carry the signal
        {
            "kind": "no_intersection",
            "pairs": [
                ["walls", "door"],
                ["walls", "window_panes"],
                ["roof", "walls"],
                ["roof_hangs", "walls"],
            ],
        },
        {"kind": "group_present", "groups": ["door", "slabs", "roof_hangs"]},
        {"kind": "count_per_storey", "group": "window", "min_each": 2, "storeys": 2},
    ],
)

_townhouse = BuildingPreset(
    id="townhouse",
    label="Townhouse",
    description="Narrow three storey row house, boxed gable roof, "
    "door-window multigroup and stacked windows.",
    reference="https://commons.wikimedia.org/wiki/File:Stella_Lowry_House,_Midway_Row_Houses,_Delaware_Avenue,_Allentown,_Buffalo,_NY.jpg",
    floorplan={"type": "RECTANGULAR", "width": 6.0, "length": 5.0},
    floors={"floor_count": 3, "floor_height": 3.0, "add_slab": True},
    roof={
        "type": "GABLE",
        "gable_type": "BOX",
        "height": 1.2,
        "thickness": 0.12,
        "outset": 0.12,
        "add_gutters": True,
    },
    facade=[
        FacadeRule(
            "multigroup",
            "ground_front_wall",
            (0,),
            {"size_offset": {"size": [2.0, 2.4]}},
        ),
        FacadeRule(
            "window", "front_walls", (1, 2), {"size_offset": {"size": [1.4, 1.8]}}
        ),
        FacadeRule(
            "window", "side_walls", (1, 2), {"size_offset": {"size": [1.2, 1.6]}}
        ),
    ],
    checks=[
        {"kind": "group_present", "groups": ["walls", "roof", "frame", "window"]},
        # NOTE: walls/frame is exempt -- sills/thresholds are proud trim
        # that crosses jamb edges at the opening seam (T-junction class,
        # advisory per AGENTS.md); element-element pairs carry the signal
        {
            "kind": "no_intersection",
            "pairs": [
                ["walls", "door"],
                ["walls", "window_panes"],
                ["roof", "walls"],
                ["roof_hangs", "walls"],
            ],
        },
        {"kind": "group_present", "groups": ["door", "slabs", "roof_hangs"]},
        {
            "kind": "count_per_storey",
            "group": "window",
            "min_each": 2,
            "storeys": 2,
            "skip_storeys": 1,
        },
    ],
)

_apartment = BuildingPreset(
    id="apartment-block",
    label="Apartment Block",
    description="Five storey flat-roof block with a window grid, entry "
    "multigroup and post-rail balconies on the front.",
    reference="https://commons.wikimedia.org/wiki/File:Mimo%C5%88_-_panel%C3%A1k.JPG",
    floorplan={"type": "RECTANGULAR", "width": 14.0, "length": 9.0},
    floors={"floor_count": 5, "floor_height": 3.0, "add_slab": True},
    roof={
        "type": "FLAT",
        "thickness": 0.2,
        "outset": 0.15,
        "add_border": True,
        "border": 0.2,
    },
    facade=[
        FacadeRule(
            "multigroup",
            "ground_front_wall",
            (0,),
            {"size_offset": {"size": [2.4, 2.6]}},
        ),
        # -- balconies BEFORE windows: the storey face is still unsplit,
        #    so each balcony is one clean platform (no fragmented strips);
        #    array count/width mirror the window grid (14m / 4 = 3.5m bays)
        FacadeRule(
            "balcony",
            "front_walls",
            (1, 2, 3, 4),
            {
                "size_offset": {"size": [3.3, 0.2]},
                "array": {"count": 4},
            },
        ),
        FacadeRule(
            "window",
            "walls",
            (1, 2, 3, 4),
            {
                "fill_type": "GLASS_PANES",
                "array": {"count": 4},
                "size_offset": {"size": [1.6, 1.4]},
            },
        ),
    ],
    checks=[
        # -- structure: expected groups exist
        {
            "kind": "group_present",
            "groups": [
                "walls",
                "slabs",
                "roof",
                "window",
                "window_panes",
                "door",
                "frame",
                "balcony",
                "railing_posts",
                "railing_rails",
            ],
        },
        # -- nothing may interpenetrate (exact edge-triangle crossings;
        #    coplanar attachment seams and boundary grazes excluded)
        {
            "kind": "no_intersection",
            "pairs": [
                ["walls", "balcony"],
                ["balcony", "walls"],
                ["railing_posts", "balcony"],
                ["balcony", "railing_posts"],
                ["frame", "railing_posts"],
                ["frame", "balcony"],
                ["balcony", "slabs"],
                ["slabs", "balcony"],
            ],
        },
        # -- every balconyed storey (1-4; ground has none) carries
        #    comparable railing geometry
        {
            "kind": "count_per_storey",
            "group": "railing_posts",
            "min_each": 300,
            "storeys": 4,
            "skip_storeys": 1,
        },
        # -- window bays and balcony cells line up on the front elevation
        {
            "kind": "bay_alignment",
            "a": "window",
            "b": "balcony",
            "view": "front",
            "tol": 0.35,
            "tol_a": 1.6,
        },
        # -- flat-roof parapet outsets equally on all four sides
        {"kind": "symmetric_outset", "group": "roof", "tol": 0.05},
    ],
)

_modern_villa = BuildingPreset(
    id="modern-villa",
    label="Modern Villa",
    description="Two storey plus-shaped flat-roof villa with wide ribbon glazing.",
    reference="https://commons.wikimedia.org/wiki/File:Savoye_3.JPG",
    floorplan={"type": "RECTANGULAR", "width": 12.0, "length": 9.0},
    floors={"floor_count": 2, "floor_height": 3.2, "add_slab": True},
    roof={
        "type": "FLAT",
        "thickness": 0.25,
        "outset": 0.3,
        "add_border": True,
        "border": 0.25,
    },
    facade=[
        FacadeRule(
            "door",
            "ground_front_wall",
            (0,),
            {"size_offset": {"size": [1.2, 2.4]}},
        ),
        FacadeRule(
            "window",
            "front_walls",
            (0,),
            {"fill_type": "GLASS_PANES", "size_offset": {"size": [2.0, 1.6]}},
        ),
        FacadeRule(
            "window",
            "front_walls",
            (1,),
            {"fill_type": "GLASS_PANES", "size_offset": {"size": [3.0, 2.0]}},
        ),
        FacadeRule(
            "window",
            "side_walls",
            (0, 1),
            {"fill_type": "GLASS_PANES", "size_offset": {"size": [2.0, 1.6]}},
        ),
        FacadeRule(
            "window",
            "back_walls",
            (0, 1),
            {"size_offset": {"size": [2.0, 1.4]}},
        ),
    ],
    checks=[
        {"kind": "group_present", "groups": ["walls", "roof", "frame", "window"]},
        # NOTE: walls/frame is exempt -- sills/thresholds are proud trim
        # that crosses jamb edges at the opening seam (T-junction class,
        # advisory per AGENTS.md); element-element pairs carry the signal
        {
            "kind": "no_intersection",
            "pairs": [
                ["walls", "door"],
                ["walls", "window_panes"],
                ["roof", "walls"],
                ["roof_hangs", "walls"],
            ],
        },
        {"kind": "group_present", "groups": ["door", "slabs", "window_panes"]},
        {"kind": "count_per_storey", "group": "window", "min_each": 2, "storeys": 2},
    ],
)

_mediterranean = BuildingPreset(
    id="mediterranean-villa",
    label="Mediterranean Villa",
    description="Two storey hip-roof villa with wall-rail balconies and boxed windows.",
    reference="https://commons.wikimedia.org/wiki/File:(1)Mediterranean_house_Vaucluse.jpg",
    floorplan={"type": "RECTANGULAR", "width": 9.0, "length": 7.0},
    floors={"floor_count": 2, "floor_height": 3.0, "add_slab": True},
    roof={
        "type": "HIP",
        "height": 1.4,
        "thickness": 0.15,
        "outset": 0.2,
        "add_gutters": True,
    },
    facade=[
        FacadeRule(
            "door", "ground_front_wall", (0,), {"size_offset": {"size": [1.2, 2.2]}}
        ),
        FacadeRule(
            "balcony",
            "front_walls",
            (1,),
            {"rail": {"fill": "WALL"}, "size_offset": {"size": [5.0, 0.2]}},
        ),
        FacadeRule(
            "window", "side_walls", (0, 1), {"size_offset": {"size": [1.4, 1.6]}}
        ),
    ],
    checks=[
        {"kind": "group_present", "groups": ["walls", "roof", "frame", "window"]},
        # NOTE: walls/frame is exempt -- sills/thresholds are proud trim
        # that crosses jamb edges at the opening seam (T-junction class,
        # advisory per AGENTS.md); element-element pairs carry the signal
        {
            "kind": "no_intersection",
            "pairs": [
                ["walls", "door"],
                ["walls", "window_panes"],
                ["roof", "walls"],
                ["roof_hangs", "walls"],
            ],
        },
        {
            "kind": "group_present",
            "groups": ["door", "balcony", "slabs", "railing_walls", "roof_hangs"],
        },
        {"kind": "count_per_storey", "group": "window", "min_each": 2, "storeys": 2},
    ],
)

_corner_shop = BuildingPreset(
    id="corner-shop",
    label="Corner Shop",
    description="Two storey corner shop with a glazed shopfront and windows above.",
    reference="https://commons.wikimedia.org/wiki/File:Bill%27s_Corner_Market_-_fmr_Frederick_Karcher_dry_goods_store,_Felton%27s_Flower_Shop_et_al._-_Buffalo,_New_York_-_20201109.jpg",
    floorplan={"type": "RECTANGULAR", "width": 8.0, "length": 8.0},
    floors={"floor_count": 2, "floor_height": 3.5, "add_slab": True},
    roof={
        "type": "FLAT",
        "thickness": 0.2,
        "outset": 0.15,
        "add_border": True,
        "border": 0.2,
    },
    facade=[
        FacadeRule(
            "multigroup",
            "ground_front_wall",
            (0,),
            {"size_offset": {"size": [4.0, 2.8]}},
        ),
        FacadeRule(
            "window",
            "front_walls",
            (1,),
            {"array": {"count": 3}, "size_offset": {"size": [1.4, 1.6]}},
        ),
    ],
    checks=[
        {"kind": "group_present", "groups": ["walls", "roof", "frame", "window"]},
        # NOTE: walls/frame is exempt -- sills/thresholds are proud trim
        # that crosses jamb edges at the opening seam (T-junction class,
        # advisory per AGENTS.md); element-element pairs carry the signal
        {
            "kind": "no_intersection",
            "pairs": [
                ["walls", "door"],
                ["walls", "window_panes"],
                ["roof", "walls"],
                ["roof_hangs", "walls"],
            ],
        },
        {"kind": "group_present", "groups": ["door", "slabs"]},
        {
            "kind": "count_per_storey",
            "group": "window",
            "min_each": 3,
            "storeys": 1,
            "skip_storeys": 1,
        },
    ],
)

_warehouse = BuildingPreset(
    id="warehouse",
    label="Warehouse",
    description="Single tall volume with a boxed gable roof, double loading "
    "door and sparse bar windows.",
    reference="https://commons.wikimedia.org/wiki/File:Daiwa_Logistics_Tosu_Logistics_Center.jpg",
    floorplan={"type": "RECTANGULAR", "width": 16.0, "length": 10.0},
    floors={"floor_count": 1, "floor_height": 6.0, "add_slab": False},
    roof={
        "type": "GABLE",
        "gable_type": "BOX",
        "height": 2.0,
        "thickness": 0.15,
        "outset": 0.2,
        "add_gutters": True,
    },
    facade=[
        FacadeRule(
            "door",
            "ground_front_wall",
            (0,),
            {"double_door": True, "size_offset": {"size": [3.5, 4.0]}},
        ),
        FacadeRule(
            "window",
            "side_walls",
            (0,),
            {
                "fill_type": "BAR",
                "array": {"count": 3},
                "size_offset": {"size": [1.5, 1.0]},
            },
        ),
    ],
    checks=[
        {
            "kind": "group_present",
            "groups": [
                "walls",
                "roof",
                "frame",
                "window",
                "door",
                "window_bars",
                "roof_hangs",
            ],
        },
        {
            "kind": "no_intersection",
            "pairs": [
                ["walls", "door"],
                ["walls", "window_bars"],
                ["roof_hangs", "walls"],
            ],
        },
        {"kind": "symmetric_outset", "group": "roof", "tol": 0.05},
    ],
)

_office = BuildingPreset(
    id="office-block",
    label="Office Block",
    description="Six storey flat-roof office with a dense glass window grid "
    "(curtain-wall approximation) and entrance group.",
    reference="https://commons.wikimedia.org/wiki/File:Seagram_Building_(35098307116).jpg",
    floorplan={"type": "RECTANGULAR", "width": 14.0, "length": 10.0},
    floors={"floor_count": 6, "floor_height": 3.0, "add_slab": True},
    roof={
        "type": "FLAT",
        "thickness": 0.25,
        "outset": 0.2,
        "add_border": True,
        "border": 0.25,
    },
    facade=[
        FacadeRule(
            "multigroup",
            "ground_front_wall",
            (0,),
            {"size_offset": {"size": [3.0, 2.8]}},
        ),
        FacadeRule(
            "window",
            "walls",
            (1, 2, 3, 4, 5),
            {
                "fill_type": "GLASS_PANES",
                "array": {"count": 4},
                "size_offset": {"size": [1.8, 1.6]},
            },
        ),
    ],
    checks=[
        {"kind": "group_present", "groups": ["walls", "roof", "frame", "window"]},
        # NOTE: walls/frame is exempt -- sills/thresholds are proud trim
        # that crosses jamb edges at the opening seam (T-junction class,
        # advisory per AGENTS.md); element-element pairs carry the signal
        {
            "kind": "no_intersection",
            "pairs": [
                ["walls", "door"],
                ["walls", "window_panes"],
                ["roof", "walls"],
                ["roof_hangs", "walls"],
            ],
        },
        {"kind": "group_present", "groups": ["door", "slabs", "window_panes"]},
        {
            "kind": "count_per_storey",
            "group": "window",
            "min_each": 4,
            "storeys": 5,
            "skip_storeys": 1,
        },
    ],
)

for _p in (
    _suburban,
    _townhouse,
    _apartment,
    _modern_villa,
    _mediterranean,
    _corner_shop,
    _warehouse,
    _office,
):
    _register(_p)


# ---------------------------------------------------------------- builder


def _scale(plan_kwargs, width_scale, depth_scale):
    kwargs = dict(plan_kwargs)
    if "width" in kwargs:
        kwargs["width"] = round(kwargs["width"] * width_scale, 4)
    if "length" in kwargs:
        kwargs["length"] = round(kwargs["length"] * depth_scale, 4)
    return kwargs


def build_preset(
    preset, floors=None, width_scale=1.0, depth_scale=1.0, assign_materials=True
):
    """Build a complete building from a preset recipe.

    floors       -- floor-count override (default: preset value)
    width/depth  -- uniform scale multipliers for the floorplan footprint
    assign_materials -- apply default BT_<group> materials when done

    Returns OpResult; result.created_object is the finished building.
    """
    summaries = []

    def record(feature, res):
        summaries.append(
            {
                "feature": feature,
                "status": res.status,
                "matgroup_counts": res.matgroup_counts,
                "errors": res.errors[:1],
            }
        )
        return res

    def build():
        fp_kwargs = _scale(preset.floorplan, width_scale, depth_scale)
        res = apply_feature("floorplan", options_from_dict(FloorplanOptions, fp_kwargs))
        record("floorplan", res)
        if not res.ok:
            return res
        obj = bpy.data.objects[res.created_object]

        floors_kwargs = dict(preset.floors)
        if floors is not None:
            floors_kwargs["floor_count"] = floors
        floor_count = floors_kwargs.get("floor_count", 1)
        floor_height = floors_kwargs.get("floor_height", preset.floor_height)
        if floors_kwargs:
            res = apply_feature(
                "floor", options_from_dict(FloorOptions, floors_kwargs), FaceTarget(obj)
            )
            record("floor", res)
            if not res.ok:
                return res

        if preset.roof:
            res = apply_feature(
                "roof",
                options_from_dict(RoofOptions, preset.roof),
                FaceTarget(obj, [select(obj, "top_face")[0]]),
            )
            record("roof", res)
            if not res.ok:
                return res

        for rule in preset.facade:
            storeys = rule.storeys if rule.storeys else tuple(range(floor_count))
            options = options_from_dict(OPTION_TYPES[rule.feature], dict(rule.options))
            faces = select(
                obj,
                rule.faces,
                floor_height=floor_height,
                storeys=storeys,
                group="walls",
            )
            if not faces:
                summaries.append(
                    {
                        "feature": rule.feature,
                        "status": "skipped",
                        "matgroup_counts": {},
                        "errors": [],
                        "warnings": ["no faces matched %r" % rule.faces],
                    }
                )
                continue
            res = apply_feature(rule.feature, options, FaceTarget(obj, faces))
            record(rule.feature, res)
            if not res.ok:
                return res

        report = validate_object(obj, include_geometry=False)
        if assign_materials:
            from ..building.default_materials import apply_default_materials

            apply_default_materials(obj)
        return OpResult(
            "ok",
            "preset:%s" % preset.id,
            object_name=obj.name,
            created_object=obj.name,
            matgroup_counts=report["matgroups"]["groups"],
            warnings=report["problems"],
        )

    try:
        return build()
    except Exception as exc:
        return OpResult(
            "error",
            "preset:%s" % preset.id,
            errors=["%s: %s" % (type(exc).__name__, exc)],
        )


def preset_items():
    """(id, label) pairs in registration order, for UI enums."""
    return [(p.id, p.label, p.description) for p in PRESETS.values()]


def check_preset(preset, **build_kwargs):
    """Build a preset and run its declarative geometry checks.

    Returns {"build": OpResult, "checks": run_checks report}; the checks
    report follows run_checks ({"ok", "failures", "results"}) and is
    {"ok": False, "results": []} when the build itself fails.
    """
    from .checks import run_checks

    res = build_preset(preset, **build_kwargs)
    if not res.ok:
        return {
            "build": res,
            "checks": {"ok": False, "failures": [], "results": []},
        }
    obj = bpy.data.objects.get(res.created_object or "")
    report = (
        run_checks(obj, preset.checks)
        if obj
        else {"ok": False, "failures": [], "results": []}
    )
    return {"build": res, "checks": report}

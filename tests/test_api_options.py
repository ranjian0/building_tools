"""Guardrails keeping `btools/api/options.py` dataclasses in sync with the
Blender property groups they mirror.

- Drift test: leaf fields of every options dataclass must exist on the
  corresponding PropertyGroup (and vice versa), modulo the documented
  ignore lists (mixin aliases, UI-only props).
- Round-trip test: options -> prop group -> dict must preserve every leaf
  value/name.
"""

import dataclasses
import enum
import math
import unittest

import bpy
from mathutils import Vector

import btools
from btools.api.options import (
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
from btools.building.balcony import BalconyProperty
from btools.building.door import DoorProperty
from btools.building.fill import FillProperty
from btools.building.floor import FloorProperty
from btools.building.floorplan import FloorplanProperty
from btools.building.multigroup import MultigroupProperty
from btools.building.roof import RoofProperty
from btools.building.stairs import StairsProperty
from btools.building.window import WindowProperty

PAIRS = [
    ("floorplan", FloorplanOptions, FloorplanProperty),
    ("floor", FloorOptions, FloorProperty),
    ("roof", RoofOptions, RoofProperty),
    ("door", DoorOptions, DoorProperty),
    ("window", WindowOptions, WindowProperty),
    ("multigroup", MultigroupOptions, MultigroupProperty),
    ("balcony", BalconyOptions, BalconyProperty),
    ("stairs", StairsOptions, StairsProperty),
    ("fill", FillOptions, FillProperty),
]

# -- names present on the PropertyGroup but intentionally not on the options
#    dataclass (mixin aliases / UI state)
PROP_ONLY = {
    BalconyProperty: {"count", "size", "offset", "wall_dimensions"},
    StairsProperty: {"count", "size", "offset", "wall_dimensions"},
    DoorProperty: {"wall_dimensions"},
    WindowProperty: {"wall_dimensions"},
    MultigroupProperty: {"wall_dimensions"},
}

# -- getter/setter aliases and UI toggles inside nested groups: they mirror
#    the vector/enum values already covered by their parent props
NESTED_SKIP = {
    "size_width",
    "size_height",
    "offset_horizontal",
    "offset_vertical",
    "show_props",
    "show_extra_props",
}

SCENE_NAME = "bt_api_options_test_prop"

# -- arch sub-options depend on runtime init() state (parent_height ID-prop),
#    so they can't round-trip on a bare property group; drift is still checked
ROUND_TRIP_SKIP = {"arch"}

# -- registration order matters: pointer-property targets must be registered
#    before the groups that reference them
REGISTER_ORDER = [
    btools.building.arch.ArchProperty,
    btools.building.array.ArrayProperty,
    btools.building.sizeoffset.SizeOffsetProperty,
    btools.building.fill.FillPanel,
    btools.building.fill.FillGlassPanes,
    btools.building.fill.FillLouver,
    btools.building.fill.FillBars,
    btools.building.railing.PostFillProperty,
    btools.building.railing.RailFillProperty,
    btools.building.railing.WallFillProperty,
    btools.building.railing.RailProperty,
    FloorplanProperty,
    FloorProperty,
    RoofProperty,
    DoorProperty,
    WindowProperty,
    MultigroupProperty,
    BalconyProperty,
    StairsProperty,
    FillProperty,
]


def register_all():
    for cls in REGISTER_ORDER:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass  # already registered


def unregister_all():
    for cls in reversed(REGISTER_ORDER):
        try:
            bpy.utils.unregister_class(cls)
        except (ValueError, KeyError):
            pass


def dc_leaves(options, prefix="", skip_none=False):
    """{(prefix,)name: value} for an options dataclass instance.
    skip_none drops None-valued leaves (None = 'delegate to the prop's
    init()', so they have no counterpart value to compare)."""
    out = {}
    for f in dataclasses.fields(options):
        value = getattr(options, f.name)
        if value is None:
            if skip_none:
                continue
        if dataclasses.is_dataclass(value):
            for k, v in dc_leaves(value, prefix + f.name + ".", skip_none).items():
                out[k] = v
        else:
            out[prefix + f.name] = value
    return out


def _is_prop_group_struct(fixed):
    """fixed_type returns a bpy_struct wrapper (not a class) for registered
    groups; walk the RNA base chain to confirm it is a PropertyGroup."""
    rna = getattr(fixed, "bl_rna", None)
    while rna is not None:
        if rna.identifier == "PropertyGroup":
            return True
        rna = rna.base
    return False


def prop_leaves(prop, prefix="", skip=()):
    """{(prefix,)name: value} for a PropertyGroup instance."""
    out = {}
    for p in prop.bl_rna.properties:
        if p.identifier in {"rna_type"} or p.identifier in skip:
            continue
        if p.type == "POINTER":
            fixed = getattr(p, "fixed_type", None)
            if fixed is not None and _is_prop_group_struct(fixed):
                child = getattr(prop, p.identifier)
                for k, v in prop_leaves(child, prefix + p.identifier + ".", skip).items():
                    out[k] = v
        elif p.type in {"INT", "FLOAT", "BOOLEAN", "ENUM", "STRING"} and not p.is_readonly:
            out[prefix + p.identifier] = getattr(prop, p.identifier)
    return out


def _strip_nones(value):
    if isinstance(value, dict):
        return {k: _strip_nones(v) for k, v in value.items() if v is not None}
    return value


def comparable(value):
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, Vector):
        return tuple(value)
    if isinstance(value, tuple):
        return tuple(comparable(v) for v in value)
    if isinstance(value, float):
        return round(value, 5)  # rna stores float32
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    return value


# implicit/alias props on every PropertyGroup
ALWAYS_SKIP = {"name"}


class TestOptionsDrift(unittest.TestCase):
    def test_pairs_declared(self):
        self.assertEqual(len(PAIRS), 9, "every feature must be covered")

    def test_no_drift(self):
        register_all()
        problems = []
        for name, options_cls, prop_cls in PAIRS:
            setattr(bpy.types.Scene, SCENE_NAME, bpy.props.PointerProperty(type=prop_cls))
            try:
                inst = getattr(bpy.context.scene, SCENE_NAME)
                dc = dc_leaves(options_cls())
                rna = prop_leaves(inst, skip=NESTED_SKIP)
            finally:
                delattr(bpy.types.Scene, SCENE_NAME)

            ignore = PROP_ONLY.get(prop_cls, set())
            for leaf in dc:
                if leaf not in rna:
                    problems.append("%s: options field %r missing on PropertyGroup" % (name, leaf))
            for leaf in rna:
                if leaf.split(".")[-1] in ALWAYS_SKIP:
                    continue
                if "." not in leaf and leaf.split(".")[-1] in ignore:
                    continue
                if leaf not in dc:
                    problems.append("%s: PropertyGroup prop %r missing on options dataclass" % (name, leaf))
        unregister_all()
        self.assertEqual(problems, [], "\n".join(problems))


class TestOptionsRoundTrip(unittest.TestCase):
    def test_round_trip(self):
        register_all()
        problems = []
        for name, options_cls, prop_cls in PAIRS:
            setattr(bpy.types.Scene, SCENE_NAME, bpy.props.PointerProperty(type=prop_cls))
            try:
                inst = getattr(bpy.context.scene, SCENE_NAME)
                options = options_cls()
                payload = _strip_nones({
                    k: v for k, v in dataclasses.asdict(options).items()
                    if k not in ROUND_TRIP_SKIP
                })
                btools.utils.prop_from_dict(inst, payload)
                got = prop_leaves(inst, skip=NESTED_SKIP)
                want = dc_leaves(options, skip_none=True)
            finally:
                delattr(bpy.types.Scene, SCENE_NAME)

            want = {
                k: v for k, v in want.items()
                if k.split(".")[0] not in ROUND_TRIP_SKIP
            }

            for leaf, expected in want.items():
                if leaf not in got:
                    problems.append("%s: leaf %r lost in round-trip" % (name, leaf))
                    continue
                if comparable(got[leaf]) != comparable(expected):
                    problems.append(
                        "%s: leaf %r changed: %r -> %r" % (name, leaf, expected, got[leaf])
                    )
        unregister_all()
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()

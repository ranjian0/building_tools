from dataclasses import asdict

import bpy

from ..utils import dict_from_prop, get_selected_face_dimensions, prop_from_dict
from .options import (
    BalconyOptions,
    DoorOptions,
    FloorOptions,
    FloorplanOptions,
    MultigroupOptions,
    RoofOptions,
    WindowOptions,
)


def register_property(cls):
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        pass  # XXX Already registered


def create_floorplan(options: FloorplanOptions):
    from ..building.floorplan import FloorplanProperty
    from ..building.floorplan.floorplan_ops import build

    register_property(FloorplanProperty)
    bpy.types.Scene.floorplan_prop = bpy.props.PointerProperty(type=FloorplanProperty)  # type: ignore[attr-defined]
    prop = bpy.context.scene.floorplan_prop  # type: ignore[union-attr]

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)
    # -- create floorplan
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.floorplan_prop  # type: ignore[attr-defined]

    return result


def create_floors(options: FloorOptions):
    from ..building.floor import FloorProperty
    from ..building.floor.floor_ops import build

    register_property(FloorProperty)
    bpy.types.Scene.floor_prop = bpy.props.PointerProperty(type=FloorProperty)  # type: ignore[attr-defined]
    prop = bpy.context.scene.floor_prop  # type: ignore[union-attr]

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.floor_prop  # type: ignore[attr-defined]

    return result


def create_door(options: DoorOptions):
    from ..building.arch import ArchProperty
    from ..building.array import ArrayProperty
    from ..building.sizeoffset import SizeOffsetProperty

    register_property(ArchProperty)
    register_property(ArrayProperty)
    register_property(SizeOffsetProperty)

    from ..building.fill import FillGlassPanes, FillLouver, FillPanel

    register_property(FillPanel)
    register_property(FillLouver)
    register_property(FillGlassPanes)

    from ..building.door import DoorProperty
    from ..building.door.door_ops import build

    register_property(DoorProperty)

    bpy.types.Scene.door_prop = bpy.props.PointerProperty(type=DoorProperty)  # type: ignore[attr-defined]
    prop = bpy.context.scene.door_prop  # type: ignore[union-attr]
    prop.init(get_selected_face_dimensions(bpy.context))

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)

    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.door_prop  # type: ignore[attr-defined]

    return result


def create_window(options: WindowOptions):
    from ..building.arch import ArchProperty
    from ..building.array import ArrayProperty
    from ..building.sizeoffset import SizeOffsetProperty

    register_property(ArchProperty)
    register_property(ArrayProperty)
    register_property(SizeOffsetProperty)

    from ..building.fill import FillBars, FillGlassPanes, FillLouver

    register_property(FillBars)
    register_property(FillLouver)
    register_property(FillGlassPanes)

    from ..building.window import WindowProperty
    from ..building.window.window_ops import build

    register_property(WindowProperty)

    bpy.types.Scene.window_prop = bpy.props.PointerProperty(type=WindowProperty)  # type: ignore[attr-defined]
    prop = bpy.context.scene.window_prop  # type: ignore[union-attr]
    prop.init(get_selected_face_dimensions(bpy.context))

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)

    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.window_prop  # type: ignore[attr-defined]

    return result


def create_multigroup(options: MultigroupOptions):
    from ..building.arch import ArchProperty
    from ..building.array import ArrayProperty
    from ..building.sizeoffset import SizeOffsetProperty

    register_property(ArchProperty)
    register_property(ArrayProperty)
    register_property(SizeOffsetProperty)

    from ..building.fill import FillBars, FillGlassPanes, FillLouver, FillPanel

    register_property(FillBars)
    register_property(FillPanel)
    register_property(FillLouver)
    register_property(FillGlassPanes)

    from ..building.multigroup import MultigroupProperty
    from ..building.multigroup.multigroup_ops import build

    register_property(MultigroupProperty)

    bpy.types.Scene.multigroup_prop = bpy.props.PointerProperty(type=MultigroupProperty)  # type: ignore[attr-defined]
    prop = bpy.context.scene.multigroup_prop  # type: ignore[union-attr]
    prop.init(get_selected_face_dimensions(bpy.context))

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)
    # -- create multigroup
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.multigroup_prop  # type: ignore[attr-defined]

    return result


def create_roof(options: RoofOptions):
    from ..building.roof import RoofProperty
    from ..building.roof.roof_ops import build

    register_property(RoofProperty)
    bpy.types.Scene.roof_prop = bpy.props.PointerProperty(type=RoofProperty)  # type: ignore[attr-defined]
    prop = bpy.context.scene.roof_prop  # type: ignore[union-attr]

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)
    # -- create floorplan
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.roof_prop  # type: ignore[attr-defined]

    return result


def create_balcony(options: BalconyOptions):
    from ..building.array import ArrayProperty
    from ..building.railing import (
        PostFillProperty,
        RailFillProperty,
        RailProperty,
        WallFillProperty,
    )
    from ..building.sizeoffset import SizeOffsetProperty

    register_property(ArrayProperty)
    register_property(SizeOffsetProperty)
    register_property(RailFillProperty)
    register_property(PostFillProperty)
    register_property(WallFillProperty)
    register_property(RailProperty)

    from ..building.balcony import BalconyProperty
    from ..building.balcony.balcony_ops import build

    register_property(BalconyProperty)
    bpy.types.Scene.balcony_prop = bpy.props.PointerProperty(type=BalconyProperty)  # type: ignore[attr-defined]
    prop = bpy.context.scene.balcony_prop  # type: ignore[union-attr]
    prop.init(get_selected_face_dimensions(bpy.context))

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)
    # -- create floorplan
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.balcony_prop  # type: ignore[attr-defined]

    return result

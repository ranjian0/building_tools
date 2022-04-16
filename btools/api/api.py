import bpy
from dataclasses import asdict
from .options import (
    FloorplanOptions,
    FloorOptions,
    DoorOptions,
    WindowOptions
)
from ...btools.utils import (
    dict_from_prop, 
    prop_from_dict, 
    get_selected_face_dimensions
)

def register_property(cls):
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        pass  # XXX Already registered


def create_floorplan(options: FloorplanOptions):
    from ...btools.building.floorplan import FloorplanProperty
    from ...btools.building.floorplan.floorplan_ops import build
    register_property(FloorplanProperty)
    bpy.types.Scene.floorplan_prop = bpy.props.PointerProperty(type=FloorplanProperty)
    prop = bpy.context.scene.floorplan_prop

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)
    # -- create floorplan
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.floorplan_prop

    return result


def create_floors(options: FloorOptions):
    from ...btools.building.floor import FloorProperty
    from ...btools.building.floor.floor_ops import build
    register_property(FloorProperty)
    bpy.types.Scene.floor_prop = bpy.props.PointerProperty(type=FloorProperty)
    prop = bpy.context.scene.floor_prop 

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.floor_prop

    return result


def create_door(options: DoorOptions):
    from ...btools.building.arch import ArchProperty
    from ...btools.building.array import ArrayProperty
    from ...btools.building.sizeoffset import SizeOffsetProperty
    register_property(ArchProperty)
    register_property(ArrayProperty)
    register_property(SizeOffsetProperty)

    from ...btools.building.fill import FillPanel, FillLouver, FillGlassPanes
    register_property(FillPanel)
    register_property(FillLouver)
    register_property(FillGlassPanes)

    from ...btools.building.door import DoorProperty
    from ...btools.building.door.door_ops import build
    register_property(DoorProperty)

    bpy.types.Scene.door_prop = bpy.props.PointerProperty(type=DoorProperty)
    prop = bpy.context.scene.door_prop
    prop.init(get_selected_face_dimensions(bpy.context)) 

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)

    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.door_prop

    return result


def create_window(options: WindowOptions):
    from ...btools.building.arch import ArchProperty
    from ...btools.building.array import ArrayProperty
    from ...btools.building.sizeoffset import SizeOffsetProperty
    register_property(ArchProperty)
    register_property(ArrayProperty)
    register_property(SizeOffsetProperty)

    from ...btools.building.fill import FillBars, FillLouver, FillGlassPanes
    register_property(FillBars)
    register_property(FillLouver)
    register_property(FillGlassPanes)

    from ...btools.building.window import WindowProperty
    from ...btools.building.window.window_ops import build
    register_property(WindowProperty)

    bpy.types.Scene.window_prop = bpy.props.PointerProperty(type=WindowProperty)
    prop = bpy.context.scene.window_prop 
    prop.init(get_selected_face_dimensions(bpy.context))

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(asdict(options))
    prop_from_dict(prop, props_dict)

    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.window_prop


def create_multigroup(**kwargs):
    from ...btools.building.arch import ArchProperty
    from ...btools.building.array import ArrayProperty
    from ...btools.building.sizeoffset import SizeOffsetProperty
    register_property(ArchProperty)
    register_property(ArrayProperty)
    register_property(SizeOffsetProperty)

    from ...btools.building.fill import FillBars, FillPanel, FillLouver, FillGlassPanes
    register_property(FillBars)
    register_property(FillPanel)
    register_property(FillLouver)
    register_property(FillGlassPanes)

    from ...btools.building.multigroup import MultigroupProperty
    from ...btools.building.multigroup.multigroup_ops import build
    register_property(MultigroupProperty)

    bpy.types.Scene.multigroup_prop = bpy.props.PointerProperty(type=MultigroupProperty)
    prop = bpy.context.scene.multigroup_prop 

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(kwargs)
    prop_from_dict(prop, props_dict)
    # -- create floorplan
    prop.init(get_selected_face_dimensions(bpy.context))
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.multigroup_prop


def create_roof(**kwargs):
    from ...btools.building.roof import RoofProperty
    from ...btools.building.roof.roof_ops import build
    register_property(RoofProperty)
    bpy.types.Scene.roof_prop = bpy.props.PointerProperty(type=RoofProperty)
    prop = bpy.context.scene.roof_prop 

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(kwargs)
    prop_from_dict(prop, props_dict)
    # -- create floorplan
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.roof_prop

    return result


def create_balcony(**kwargs):
    from ...btools.building.array import ArrayProperty
    from ...btools.building.sizeoffset import SizeOffsetProperty
    from ...btools.building.railing import RailProperty, RailFillProperty, PostFillProperty, WallFillProperty
    register_property(ArrayProperty)
    register_property(SizeOffsetProperty)
    register_property(RailFillProperty)
    register_property(PostFillProperty)
    register_property(WallFillProperty)
    register_property(RailProperty)

    from ...btools.building.balcony import BalconyProperty
    from ...btools.building.balcony.balcony_ops import build
    register_property(BalconyProperty)
    bpy.types.Scene.balcony_prop = bpy.props.PointerProperty(type=BalconyProperty)
    prop = bpy.context.scene.balcony_prop 
    prop.init(get_selected_face_dimensions(bpy.context))

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(kwargs)
    prop_from_dict(prop, props_dict)
    # -- create floorplan
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.balcony_prop

    return result
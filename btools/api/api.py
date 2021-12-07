import bpy
from contextlib import contextmanager
from btools.utils import dict_from_prop, prop_from_dict

def register_property(cls):
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        pass  # XXX Already registered


def create_floorplan(**kwargs):
    from btools.building.floorplan import FloorplanProperty
    from btools.building.floorplan.floorplan_ops import build
    register_property(FloorplanProperty)
    bpy.types.Scene.floorplan_prop = bpy.props.PointerProperty(type=FloorplanProperty)
    prop = bpy.context.scene.floorplan_prop

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(kwargs)
    prop_from_dict(prop, props_dict)
    # -- create floorplan
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.floorplan_prop

    return result


def create_floors(**kwargs):
    from btools.building.floor import FloorProperty
    from btools.building.floor.floor_ops import build
    register_property(FloorProperty)
    bpy.types.Scene.floor_prop = bpy.props.PointerProperty(type=FloorProperty)
    prop = bpy.context.scene.floor_prop 

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(kwargs)
    prop_from_dict(prop, props_dict)
    # -- create floorplan
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.floor_prop

    return result


def create_door(**kwargs):
    from btools.building.arch import ArchProperty
    from btools.building.array import ArrayProperty
    from btools.building.sizeoffset import SizeOffsetProperty
    register_property(ArchProperty)
    register_property(ArrayProperty)
    register_property(SizeOffsetProperty)

    from btools.building.fill import FillPanel, FillLouver, FillGlassPanes
    register_property(FillPanel)
    register_property(FillLouver)
    register_property(FillGlassPanes)

    from btools.building.door import DoorProperty
    from btools.building.door.door_ops import build
    from btools.utils import get_selected_face_dimensions
    register_property(DoorProperty)

    bpy.types.Scene.door_prop = bpy.props.PointerProperty(type=DoorProperty)
    prop = bpy.context.scene.door_prop 

    # -- update prop options from kwargs
    props_dict = dict_from_prop(prop)
    props_dict.update(kwargs)
    prop_from_dict(prop, props_dict)
    # -- create floorplan
    prop.init(get_selected_face_dimensions(bpy.context))
    result = build(bpy.context, prop)
    # -- unregister prop
    del bpy.types.Scene.door_prop

    return result

def create_window():
    pass 

def create_multigroup():
    pass 

def create_roof():
    pass 


def create_balcony():
    pass
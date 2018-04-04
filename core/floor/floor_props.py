import bpy
from bpy.props import *

from ..update import update_building


class FloorProperty(bpy.types.PropertyGroup):
    floor_count     = IntProperty(
        name="Floor Count", min=1, max=1000, default=1,
        description="Number of floors",
        update=update_building)

    floor_height    = FloatProperty(
        name="Floor Height", min=0.01, max=1000.0, default=1.0,
        description="Height of each floor",
        update=update_building)

    slab_thickness  = FloatProperty(
        name="Slab Height", min=0.01, max=1000.0, default=0.15,
        description="Thickness of each slab",
        update=update_building)

    slab_outset     = FloatProperty(
        name="Slab Outset", min=0.01, max=1000.0, default=0.1,
        description="Outset of each slab",
        update=update_building)

    mat_slab        = PointerProperty(type=bpy.types.Material,
        name="Slab Material", description="Material for slab faces", update=update_building)
    mat_wall        = PointerProperty(type=bpy.types.Material,
        name="Wall Material", description="Material for wall faces", update=update_building)

    def draw(self, context, layout):
        box = layout.box()

        col = box.column(align=True)
        col.prop(self, "floor_count")
        col.prop(self, "floor_height")

        col = box.column(align=True)
        col.prop(self, "slab_thickness")
        col.prop(self, "slab_outset")

        col = box.column(align=True)
        col.prop(self, "mat_slab")
        col.prop(self, "mat_wall")

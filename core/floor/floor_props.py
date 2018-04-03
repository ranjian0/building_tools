import bpy
from bpy.props import *

class FloorProperty(bpy.types.PropertyGroup):
    floor_count     = IntProperty(
        name="Floor Count", description="Number of floors", min=1, max=1000, default=1,
        update=update_building)

    floor_height    = FloatProperty(
        name="Floor Height", description="Height of each floor", min=0.01, max=1000.0, default=1.0,
        update=update_building)

    slab_thickness  = FloatProperty(
        name="Slab Height", description="Thickness of each slab", min=0.01, max=1000.0, default=0.15,
        update=update_building)

    slab_outset     = FloatProperty(
        name="Slab Outset", description="Outset of each slab", min=0.01, max=1000.0, default=0.1,
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

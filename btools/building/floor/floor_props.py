import bpy
from bpy.props import IntProperty, FloatProperty, BoolProperty
from ...utils import get_scaled_unit


class FloorProperty(bpy.types.PropertyGroup):
    floor_count: IntProperty(
        name="Floor Count", min=1, max=1000, default=1, description="Number of floors"
    )

    floor_height: FloatProperty(
        name="Floor Height",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(1000.0),
        default=get_scaled_unit(2.0),
        unit="LENGTH",
        description="Height of each floor",
    )

    add_slab: BoolProperty(
        name="Add Slab", default=True, description="Add slab between each floor"
    )

    add_columns: BoolProperty(
        name="Add Columns", default=False, description="Add Columns"
    )

    slab_thickness: FloatProperty(
        name="Slab Thickness",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(1000.0),
        default=get_scaled_unit(0.2),
        unit="LENGTH",
        description="Thickness of each slab",
    )

    slab_outset: FloatProperty(
        name="Slab Outset",
        min=get_scaled_unit(0.0),
        max=get_scaled_unit(10.0),
        default=get_scaled_unit(0.1),
        unit="LENGTH",
        description="Outset of each slab",
    )

    def draw(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, "floor_count")
        col.prop(self, "floor_height")

        col = layout.column(align=True)
        col.prop(self, "add_slab")
        if self.add_slab:
            col.prop(self, "slab_thickness")
            col.prop(self, "slab_outset")

        layout.prop(self, "add_columns")

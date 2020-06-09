import bpy
from bpy.props import IntProperty, FloatProperty, BoolProperty


class FloorProperty(bpy.types.PropertyGroup):
    floor_count: IntProperty(
        name="Floor Count", min=1, max=1000, default=1, description="Number of floors"
    )

    floor_height: FloatProperty(
        name="Floor Height",
        min=0.01,
        max=1000.0,
        default=2.0,
        description="Height of each floor",
    )

    add_slab: BoolProperty(
        name="Add Slab", default=True, description="Add slab between each floor"
    )

    slab_thickness: FloatProperty(
        name="Slab Thickness",
        min=0.01,
        max=1000.0,
        default=0.2,
        description="Thickness of each slab",
    )

    slab_outset: FloatProperty(
        name="Slab Outset",
        min=0.0,
        max=10.0,
        default=0.1,
        description="Outset of each slab",
    )

    def draw(self, context, layout):
        box = layout.box()

        col = box.column(align=True)
        col.prop(self, "floor_count")
        col.prop(self, "floor_height")

        col = box.column(align=True)
        col.prop(self, "add_slab")
        if self.add_slab:
            col.prop(self, "slab_thickness")
            col.prop(self, "slab_outset")

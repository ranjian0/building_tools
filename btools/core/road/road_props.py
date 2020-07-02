import bpy
from bpy.props import (
    FloatProperty
)


class RoadProperty(bpy.types.PropertyGroup):
    width: FloatProperty(
        name="Width",
        min=0.01,
        max=50.0,
        default=4,
        unit="LENGTH",
        description="Width of road",
    )

    def init(self, wall_dimensions):
        pass

    def draw(self, context, layout):
        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "width", text="")

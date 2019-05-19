import bpy
from bpy.props import *


class RoofProperty(bpy.types.PropertyGroup):
    roof_items = [
        ("FLAT", "Flat", "", 0),
        ("GABLE", "Gable", "", 1),
        ("HIP", "Hip", "", 2),
    ]
    type: EnumProperty(
        name="Roof Type",
        items=roof_items,
        default="FLAT",
        description="Type of roof to create",
    )

    thickness: FloatProperty(
        name="Thickness",
        min=0.01,
        max=1000.0,
        default=0.1,
        description="Thickness of roof hangs",
    )

    outset: FloatProperty(
        name="Outset",
        min=0.01,
        max=1000.0,
        default=0.1,
        description="Outset of roof hangs",
    )

    height: FloatProperty(
        name="Height",
        min=0.01,
        max=1000.0,
        default=1,
        description="Height of entire roof",
    )

    o_types = [("HORIZONTAL", "Horizontal", "", 0), ("VERTICAL", "Vertical", "", 1)]
    orient: EnumProperty(
        description="Orientation of gable", items=o_types, default="HORIZONTAL"
    )

    def draw(self, context, layout):
        layout.prop(self, "type", text="")

        box = layout.box()
        if self.type == "FLAT":
            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")

        elif self.type == "GABLE":
            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")
            col.prop(self, "height")

            row = box.row(align=True)
            row.prop(self, "orient", expand=True)

        else:
            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")
            col.prop(self, "height")

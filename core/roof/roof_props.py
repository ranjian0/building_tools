import bpy
from bpy.props import EnumProperty, FloatProperty, BoolProperty


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
        max=1.0,
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

    roof_hangs: BoolProperty(
        name="Roof Hangs", default=True, description="Whether to add roof hangs"
    )

    flip_direction: BoolProperty(
        name="Flip Direction", default=False, description="Whether to change direction of roof axis"
    )

    def draw(self, context, layout):
        layout.prop(self, "type", text="")

        box = layout.box()
        if self.type == "FLAT":
            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")

        elif self.type == "GABLE":
            row = box.row(align=True)
            row.prop(self, "flip_direction", toggle=True)

            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")
            col.prop(self, "height")

            box.prop(self, "roof_hangs", toggle=True)

        else:
            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")
            col.prop(self, "height")

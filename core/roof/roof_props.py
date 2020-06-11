import bpy
from bpy.props import EnumProperty, FloatProperty


class RoofProperty(bpy.types.PropertyGroup):
    roof_items = [
        ("FLAT", "Flat", "", 0),
        ("GABLE", "Gable", "", 1),
        ("HIP", "Hip", "", 2),
    ]
    type: EnumProperty(
        name="Roof Type",
        items=roof_items,
        default="HIP",
        description="Type of roof to create",
    )

    gable_types = [
        ("OPEN", "OPEN", "", 0),
        ("BOX", "BOX", "", 1),
    ]
    gable_type: EnumProperty(
        name="Gable Type",
        items=gable_types,
        default="OPEN",
        description="Type of gable roof to create",
    )

    thickness: FloatProperty(
        name="Thickness",
        min=0.01,
        max=1.0,
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
        max=10.0,
        default=1,
        description="Height of entire roof",
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
            row.prop(self, "gable_type", expand=True)

            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")
            col.prop(self, "height")

        else:
            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")
            col.prop(self, "height")

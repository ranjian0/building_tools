import bpy
from bpy.props import EnumProperty, FloatProperty, BoolProperty


class RoofProperty(bpy.types.PropertyGroup):
    roof_types = [
        ("FLAT", "Flat", "", 0),
        ("GABLE", "Gable", "", 1),
        ("HIP", "Hip", "", 2),
    ]
    type: EnumProperty(
        name="Roof Type",
        items=roof_types,
        default="HIP",
        description="Type of roof to create",
    )

    gable_types = [
        ("OPEN", "Open", "", 0),
        ("BOX", "Box", "", 1),
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
        unit="LENGTH",
        description="Thickness of roof hangs",
    )

    outset: FloatProperty(
        name="Outset",
        min=0.01,
        max=1.0,
        default=0.1,
        unit="LENGTH",
        description="Outset of roof hangs",
    )

    height: FloatProperty(
        name="Height",
        min=0.01,
        max=10.0,
        default=1,
        unit="LENGTH",
        description="Height of entire roof",
    )

    add_border: BoolProperty(
        name="Add Border",
        default=True,
        description="Whether to add extruded border around flat roof"
    )

    border: FloatProperty(
        name="Border",
        min=0.01,
        max=1.0,
        default=0.1,
        unit="LENGTH",
        description="Width of extruded border",
    )

    def draw(self, context, layout):
        layout.prop(self, "type", text="")

        box = layout.box()
        if self.type == "FLAT":
            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")

            col.prop(self, "add_border")
            if self.add_border:
                col.prop(self, "border")

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

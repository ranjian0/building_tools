import math

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty

from ...utils import get_scaled_unit


class RoofProperty(bpy.types.PropertyGroup):
    roof_types = [
        ("FLAT", "Flat", "", 0),
        ("GABLE", "Gable", "", 1),
        ("HIP", "Hip", "", 2),
        ("FLAT_TOP", "Flat Top", "", 3),
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
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(1.0),
        default=get_scaled_unit(0.15),
        unit="LENGTH",
        description="Thickness of roof hangs",
    )

    outset: FloatProperty(
        name="Outset",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(1.0),
        default=get_scaled_unit(0.25),
        unit="LENGTH",
        description="Outset of roof hangs",
    )

    add_gutters: BoolProperty(
        name="Add Gutters",
        default=False,
        description="Add half-round gutters along the eaves",
    )

    gutter_size: FloatProperty(
        name="Gutter Size",
        min=get_scaled_unit(0.03),
        max=get_scaled_unit(0.2),
        default=get_scaled_unit(0.08),
        unit="LENGTH",
        description="Gutter radius",
    )

    add_chimney: BoolProperty(
        name="Add Chimney",
        default=False,
        description="Add a masonry chimney on the roof slope",
    )

    add_ridge_cap: BoolProperty(
        name="Ridge Cap",
        default=True,
        description="Cap the roof ridge and gable rake edges",
    )

    coping_size: FloatProperty(
        name="Coping Chamfer",
        min=0.0,
        max=get_scaled_unit(0.1),
        default=get_scaled_unit(0.02),
        unit="LENGTH",
        description="Chamfer the parapet coping top edges",
    )

    height: FloatProperty(
        name="Height",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(10.0),
        default=get_scaled_unit(1),
        unit="LENGTH",
        description="Height of entire roof",
    )

    slope_modes = [
        ("HEIGHT", "Height", "", 0),
        ("ANGLE", "Angle", "", 1),
        ("PERCENTAGE", "Percentage", "", 2),
    ]
    slope_mode: EnumProperty(
        name="Slope Mode",
        items=slope_modes,
        default="HEIGHT",
        description="Drive the roof pitch by total height, slope angle, or percentage",
    )

    slope_angle: FloatProperty(
        name="Slope Angle",
        min=math.radians(5.0),
        max=math.radians(75.0),
        default=math.radians(35.0),
        subtype="ANGLE",
        description="Pitch angle of the roof planes",
    )

    slope_percentage: FloatProperty(
        name="Slope",
        min=5.0,
        max=500.0,
        default=70.0,
        subtype="PERCENTAGE",
        description="Pitch percentage of the roof planes (100% equals 45 degrees)",
    )

    flat_height: FloatProperty(
        name="Flat Height",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(10.0),
        default=get_scaled_unit(0.8),
        unit="LENGTH",
        description="Height of the flat top section (flat-top roof)",
    )

    add_border: BoolProperty(
        name="Add Border",
        default=True,
        description="Whether to add extruded border around flat roof",
    )

    border: FloatProperty(
        name="Border",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(1.0),
        default=get_scaled_unit(0.1),
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
            self._draw_slope(col)

        elif self.type == "FLAT_TOP":
            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")
            self._draw_slope(col)
            col.prop(self, "flat_height")

        else:
            col = box.column(align=True)
            col.prop(self, "thickness")
            col.prop(self, "outset")
            self._draw_slope(col)

    def _draw_slope(self, col):
        col.prop(self, "slope_mode", text="Slope")
        if self.slope_mode == "HEIGHT":
            col.prop(self, "height")
        elif self.slope_mode == "ANGLE":
            col.prop(self, "slope_angle")
        else:
            col.prop(self, "slope_percentage")

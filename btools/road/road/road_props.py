import bpy

from bpy.props import (
    FloatProperty, BoolProperty, EnumProperty
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

    generate_left_sidewalk: BoolProperty(
        name="Generate Left Sidewalk",
        default=True,
        description="Generate a sidewalk on the left side of the road",
    )

    generate_right_sidewalk: BoolProperty(
        name="Generate Right Sidewalk",
        default=True,
        description="Generate a sidewalk on the right side of the road",
    )

    sidewalk_width: FloatProperty(
        name="Sidewalk Width",
        min=0.1,
        max=3,
        default=1,
        unit="LENGTH",
        description="Width of sidewalk",
    )

    sidewalk_height: FloatProperty(
        name="Sidewalk Height",
        min=0.01,
        max=1,
        default=0.2,
        unit="LENGTH",
        description="Height of sidewalk",
    )

    generate_shoulders: BoolProperty(
        name="Generate Shoulders",
        default=True,
        description="Generate a shoulders",
    )

    shoulder_width: FloatProperty(
        name="Shoulder Width",
        min=0.01,
        max=5,
        default=1.5,
        unit="LENGTH",
        description="Width of shoulder",
    )

    shoulder_angle: FloatProperty(
        name="Shoulder Angle",
        subtype="ANGLE",
        min=0,
        max=3.14159,
        default=0.785398,
        description="Angle of the shoulder connecting to the ground",
    )

    shoulder_height: FloatProperty(
        name="Shoulder Height",
        min=0.01,
        max=5,
        default=1.5,
        unit="LENGTH",
        description="Height of the shoulder connecting to the ground",
    )

    extrusion_types = [
        ("STRAIGHT", "Straight", "", 0),
        ("CURVE", "Curve", "", 1),
    ]

    extrusion_type: EnumProperty(
        items=extrusion_types, default="STRAIGHT", description="Extrusion mode"
    )

    interval: FloatProperty(
        name="Interval",
        min=0.1,
        default=0.5,
        unit="LENGTH",
        description="Interval of vertices",
    )

    length: FloatProperty(
        name="Length",
        min=0.01,
        default=10,
        unit="LENGTH",
        description="Length of road",
    )

    def draw(self, context, layout):
        # Shape
        box = layout.box()
        box.label(text="Shape")
        col = box.column(align=True)
        col.prop(self, "width", text="Width")
        col.prop(self, "generate_left_sidewalk", text="Left Sidewalk")
        col.prop(self, "generate_right_sidewalk", text="Right Sidewalk")

        if self.generate_left_sidewalk or self.generate_right_sidewalk:
            col.prop(self, "sidewalk_width", text="Sidewalk Width")
            col.prop(self, "sidewalk_height", text="Sidewalk Height")

        col.prop(self, "generate_shoulders", text="Shoulders")
        if self.generate_shoulders:
            col.prop(self, "shoulder_width", text="Shoulder Width")

        if not self.generate_left_sidewalk or not self.generate_right_sidewalk:
            col.prop(self, "shoulder_angle", text="Shoulder Angle")
            col.prop(self, "shoulder_height", text="Shoulder Height")

        # Extrusion
        box = layout.box()
        box.label(text="Extrusion")
        col = box.column(align=True)
        col.prop(self, "extrusion_type", text="Extrusion Mode")
        col.prop(self, "interval", text="Interval")

        if self.extrusion_type == "STRAIGHT":
            col.prop(self, "length", text="Length")
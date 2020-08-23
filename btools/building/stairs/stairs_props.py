import bpy
from bpy.props import (
    IntProperty,
    BoolProperty,
    FloatProperty,
    PointerProperty,
    EnumProperty,
)

from ..generic import SizeOffsetProperty
from ..railing.railing_props import RailProperty


class StairsProperty(bpy.types.PropertyGroup):
    depth_offset: FloatProperty(
        name="Depth Offset",
        min=0.0,
        max=100.0,
        default=0.0,
        unit="LENGTH",
        description="Depth offset of stairs",
    )

    step_count: IntProperty(
        name="Step Count", min=1, max=100, default=3, description="Number of steps"
    )

    step_width: FloatProperty(
        name="Step Width",
        min=0.01,
        max=100.0,
        default=0.2,
        unit="LENGTH",
        description="Width of each step",
    )

    step_height: FloatProperty(
        name="Step Height",
        min=0.01,
        max=100.0,
        default=0.12,
        unit="LENGTH",
        description="Height of each step",
    )

    landing_width: FloatProperty(
        name="Landing Width",
        min=0.01,
        max=100.0,
        default=1.0,
        unit="LENGTH",
        description="Width of each stairs landing",
    )

    landing: BoolProperty(
        name="Has Landing", default=True, description="Whether the stairs have a landing"
    )

    bottom_types = [
        ("FILLED", "Filled", "", 0),
        ("SLOPE", "Slope", "", 2),
        ("BLOCKED", "Blocked", "", 1),
    ]

    bottom: EnumProperty(
        name="Bottom Type",
        items=bottom_types,
        default="FILLED",
        description="Bottom type of stairs",
    )

    has_railing: BoolProperty(
        name="Add Railing", default=True, description="Whether the stairs have railing"
    )

    rail: PointerProperty(type=RailProperty)

    size_offset: PointerProperty(type=SizeOffsetProperty)

    def init(self, wall_dimensions):
        self["wall_dimensions"] = wall_dimensions
        self.size_offset.init(
            (self["wall_dimensions"][0], 0.0),
            default_size=(1.0, 0.0),
            restricted=False,
        )

    def draw(self, context, layout):
        self.size_offset.draw(context, layout)

        col = layout.column(align=True)
        col.prop(self, "depth_offset")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(self, "step_count")
        row = col.row(align=True)
        row.prop(self, "step_height")
        row.prop(self, "step_width")

        row = layout.row()
        row.prop(self, "bottom", expand=True)

        col = layout.column()
        col.prop(self, "landing")
        if self.landing:
            box = layout.box()
            col = box.column()
            col.prop(self, "landing_width")

        layout.prop(self, "has_railing")
        if self.has_railing:
            box = layout.box()
            self.rail.draw(context, box)

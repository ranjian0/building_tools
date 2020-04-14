import bpy
from bpy.props import (
    IntProperty,
    BoolProperty,
    FloatProperty,
    PointerProperty,
)

from ..railing.railing_props import RailProperty
from ..generic import SizeOffsetProperty


class StairsProperty(bpy.types.PropertyGroup):
    redo: BoolProperty()

    step_count: IntProperty(
        name="Step Count", min=1, max=100, default=3, description="Number of steps"
    )

    step_width: FloatProperty(
        name="Step Width",
        min=0.01,
        max=100.0,
        default=0.2,
        description="Width of each step",
    )

    landing_width: FloatProperty(
        name="Landing Width",
        min=0.01,
        max=100.0,
        default=0.2,
        description="Width of each stairs landing",
    )

    landing: BoolProperty(
        name="Has Landing", default=True, description="Whether to stairs have a landing"
    )

    has_railing: BoolProperty(
        name="Add Railing", default=True, description="Whether the stairs have railing"
    )

    rail: PointerProperty(type=RailProperty)

    size_offset: PointerProperty(type=SizeOffsetProperty)

    def init(self, wall_dimensions):
        self['wall_dimensions'] = wall_dimensions
        self.size_offset.init(
            (self['wall_dimensions'][0], self['wall_dimensions'][1]),
            default_size=(1.0, 0.2), default_offset=(0.0, 0.0)
        )

    def draw(self, context, layout):
        self.size_offset.draw(context, layout)

        col = layout.column(align=True)
        col.prop(self, "step_count")
        col.prop(self, "step_width")

        col.prop(self, "landing")
        if self.landing:
            box = layout.box()
            col = box.column()
            col.prop(self, "landing_width")

        layout.prop(self, "has_railing")
        if self.has_railing:
            box = layout.box()
            # box.prop_menu_enum(self, "open_side", text="Open")
            self.rail.draw(context, box)

import bpy
from bpy.props import (
    BoolProperty,
    IntProperty,
    FloatProperty,
    EnumProperty,
    PointerProperty,
)

from ..generic import SizeOffsetProperty
from ..rails import RailProperty


class StairsProperty(bpy.types.PropertyGroup):
    redo: BoolProperty()

    step_count: IntProperty(
        name="Step Count", min=1, max=100, default=3, description="Number of steps"
    )

    step_width: FloatProperty(
        name="Step Width",
        min=0.01,
        max=100.0,
        default=0.5,
        description="Width of each step",
    )

    landing_width: FloatProperty(
        name="Landing Width",
        min=0.01,
        max=100.0,
        default=1.0,
        description="Width of each stairs landing",
    )

    landing: BoolProperty(
        name="Has Landing", default=True, description="Wether to stairs have a landing"
    )

    railing: BoolProperty(
        name="Has Railing", default=True, description="Wether to stairs have a rails"
    )

    size_offset: PointerProperty(type=SizeOffsetProperty)
    rail: PointerProperty(type=RailProperty)

    direction_items = [
        ("FRONT", "Front", "", 0),
        ("LEFT", "Left", "", 1),
        ("RIGHT", "Right", "", 2),
    ]

    stair_direction: EnumProperty(
        name="Stair Direction",
        items=direction_items,
        default="FRONT",
        description="The direction to put the stairs",
    )

    def set_defaults(self):
        """ Helper function to make convinient property adjustments """
        if self.redo:
            return

        self.size_offset.size = (0.5, 1.0)
        self.redo = True

    def draw(self, context, layout):
        self.size_offset.draw(context, layout)

        col = layout.column(align=True)
        col.prop(self, "step_count")
        col.prop(self, "step_width")

        box = layout.box()
        box.prop(self, "landing", toggle=True)
        if self.landing:
            col = box.column()
            col.prop(self, "landing_width")

            row = box.row()
            row.prop_menu_enum(self, "stair_direction")

        # box = layout.box()
        # box.prop(self, "railing", toggle=True)
        # if self.railing:
        #     pass

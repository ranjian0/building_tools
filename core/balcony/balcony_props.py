import bpy
from bpy.props import BoolProperty, FloatProperty, PointerProperty

from ..railing.railing_props import RailProperty
from ..generic import SizeOffsetProperty


class BalconyProperty(bpy.types.PropertyGroup):

    slab_height: FloatProperty(
        name="Slab Height",
        min=0.01,
        max=100.0,
        default=0.2,
        description="Height of balcony slab",
    )

    depth_offset: FloatProperty(
        name="Depth Offset",
        min=0.0,
        max=100.0,
        default=0.0,
        description="Depth offset of balcony",
    )

    has_railing: BoolProperty(
        name="Add Railing", default=True, description="Whether the balcony has railing"
    )

    rail: PointerProperty(type=RailProperty)

    size_offset: PointerProperty(type=SizeOffsetProperty)

    def init(self, wall_dimensions):
        self["wall_dimensions"] = wall_dimensions
        start_y = -((wall_dimensions[1] / 2) - (self.slab_height / 2))
        self.size_offset.init(
            self["wall_dimensions"],
            default_size=(1.0, 1.0),
            default_offset=(0.0, start_y),
            restricted=False,
        )

    def draw(self, context, layout):
        self.size_offset.draw(context, layout)

        col = layout.column(align=True)
        col.prop(self, "depth_offset")

        col = layout.column(align=True)
        col.prop(self, "slab_height")

        layout.prop(self, "has_railing")
        if self.has_railing:
            box = layout.box()
            self.rail.draw(context, box)

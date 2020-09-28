import bpy
from bpy.props import BoolProperty, FloatProperty, PointerProperty

from ..generic import SizeOffsetProperty
from ..railing.railing_props import RailProperty


class BalconyProperty(bpy.types.PropertyGroup):

    slab_height: FloatProperty(
        name="Slab Height",
        min=0.01,
        max=100.0,
        default=0.2,
        unit="LENGTH",
        description="Height of balcony slab",
    )

    depth_offset: FloatProperty(
        name="Depth Offset",
        min=0.0,
        max=100.0,
        default=0.0,
        unit="LENGTH",
        description="Depth offset of balcony",
    )

    has_railing: BoolProperty(
        name="Add Railing", default=True, description="Whether the balcony has railing"
    )

    group_selection: BoolProperty(
        name="Group Selection", default=True, description="Treat adjacent face selection as a group"
    )

    rail: PointerProperty(type=RailProperty)

    size_offset: PointerProperty(type=SizeOffsetProperty)

    def init(self, wall_dimensions):
        self["wall_dimensions"] = wall_dimensions
        self.size_offset.init(
            self["wall_dimensions"],
            default_size=(1.0, 1.0),
            restricted=False,
        )

    def draw(self, context, layout):
        layout.prop(self, "group_selection")
        self.size_offset.draw(context, layout)

        col = layout.column(align=True)
        col.prop(self, "depth_offset")

        col = layout.column(align=True)
        col.prop(self, "slab_height")

        layout.prop(self, "has_railing")
        if self.has_railing:
            box = layout.box()
            self.rail.draw(context, box)

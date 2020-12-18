import bpy
from bpy.props import BoolProperty, FloatProperty, PointerProperty

from ..array import ArrayProperty, ArrayGetSet
from ..sizeoffset import SizeOffsetProperty, SizeOffsetGetSet
from ..railing.railing_props import RailProperty


class BalconyProperty(bpy.types.PropertyGroup, ArrayGetSet, SizeOffsetGetSet):
    rail: PointerProperty(type=RailProperty)
    array: PointerProperty(type=ArrayProperty)
    size_offset: PointerProperty(type=SizeOffsetProperty)

    depth: FloatProperty(
        name="Depth",
        min=0.01,
        max=100.0,
        default=1.0,
        unit="LENGTH",
        description="How much the balcony extends outwards",
    )

    depth_offset: FloatProperty(
        name="Depth Offset",
        min=0.0,
        max=100.0,
        default=0.0,
        unit="LENGTH",
        description="How much the balcony should be moved backwards",
    )

    has_railing: BoolProperty(
        name="Add Railing", default=True, description="Whether the balcony has railing"
    )

    group_selection: BoolProperty(
        name="Group Selection", default=True, description="Treat adjacent face selections as a single group"
    )

    def init(self, wall_dimensions):
        self["wall_dimensions"] = wall_dimensions
        self.size_offset.init(
            self["wall_dimensions"],
            default_size=(1.0, 0.1),
            restricted=False,
        )

    def draw(self, context, layout):
        layout.prop(self, "group_selection")
        self.size_offset.draw(context, layout)

        col = layout.column(align=True)
        col.prop(self, "depth")

        col = layout.column(align=True)
        col.prop(self, "depth_offset")

        layout.separator()
        layout.prop(self.array, "count")
        
        layout.prop(self, "has_railing")
        if self.has_railing:
            box = layout.box()
            self.rail.draw(context, box)

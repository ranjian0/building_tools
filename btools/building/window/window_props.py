import bpy
from bpy.props import (
    IntProperty,
    BoolProperty,
    EnumProperty,
    FloatProperty,
    PointerProperty
)

from ..fill import FillBars, FillLouver, FillGlassPanes
from ..generic import ArchProperty, SizeOffsetProperty, CountProperty


class WindowProperty(bpy.types.PropertyGroup):
    win_types = [
        ("CIRCULAR", "Circular", "", 0),
        ("RECTANGULAR", "Rectangular", "", 1),
    ]

    type: EnumProperty(
        name="Window Type",
        items=win_types,
        default="RECTANGULAR",
        description="Type of window",
    )

    frame_thickness: FloatProperty(
        name="Frame Thickness",
        min=0.01,
        max=1.0,
        default=0.1,
        unit="LENGTH",
        description="Thickness of window Frame",
    )

    frame_depth: FloatProperty(
        name="Frame Depth",
        min=-1.0,
        max=1.0,
        default=0.0,
        unit="LENGTH",
        description="Depth of window Frame",
    )

    window_depth: FloatProperty(
        name="Window Depth",
        min=0.0,
        max=1.0,
        default=0.05,
        unit="LENGTH",
        description="Depth of window",
    )

    resolution: IntProperty(
        name="Resolution",
        min=3,
        max=128,
        default=20,
        description="Number of segements for the circle",
    )

    add_arch: BoolProperty(
        name="Add Arch", default=False, description="Add arch over door/window"
    )

    count: CountProperty
    arch: PointerProperty(type=ArchProperty)
    size_offset: PointerProperty(type=SizeOffsetProperty)

    fill_types = [
        ("NONE", "None", "", 0),
        ("BAR", "Bar", "", 1),
        ("LOUVER", "Louver", "", 2),
        ("GLASS_PANES", "Glass_Panes", "", 3),
    ]
    fill_type: EnumProperty(
        name="Fill Type",
        items=fill_types,
        default="NONE",
        description="Type of fill for window",
    )

    bar_fill: PointerProperty(type=FillBars)
    louver_fill: PointerProperty(type=FillLouver)
    glass_fill: PointerProperty(type=FillGlassPanes)

    def init(self, wall_dimensions):
        self["wall_dimensions"] = wall_dimensions
        self.size_offset.init(
            (self["wall_dimensions"][0] / self.count, self["wall_dimensions"][1]),
            default_size=(1.0, 1.0),
            default_offset=(0.0, 0.0),
        )
        self.arch.init(wall_dimensions[1] / 2 - self.size_offset.offset.y - self.size_offset.size.y / 2)

    def draw(self, context, layout):
        box = layout.box()
        self.size_offset.draw(context, box)

        col = layout.column(align=True)
        col.row(align=True).prop(self, "type", expand=True)
        if self.type == "CIRCULAR":
            col.prop(self, "resolution", text="Resolution")

        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, "frame_depth")
        row.prop(self, "frame_thickness")
        row = col.row(align=True)
        row.prop(self, "window_depth")

        col = box.column(align=True)
        col.prop(self, "count")

        if self.type == "RECTANGULAR":
            box = layout.box()
            col = box.column(align=True)
            col.prop(self, "add_arch")
            if self.add_arch:
                self.arch.draw(context, box)

            box = layout.box()
            col = box.column(align=True)
            prop_name = (
                "Fill Type"
                if self.fill_type == "NONE"
                else self.fill_type.title().replace("_", " ")
            )
            col.prop_menu_enum(self, "fill_type", text=prop_name)

            # -- draw fill types
            fill_map = {
                "BAR": self.bar_fill,
                "LOUVER": self.louver_fill,
                "GLASS_PANES": self.glass_fill,
            }
            fill = fill_map.get(self.fill_type)
            if fill:
                fill.draw(box)

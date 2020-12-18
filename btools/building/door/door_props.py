import bpy
from bpy.props import (
    EnumProperty, 
    BoolProperty,
    FloatProperty, 
    PointerProperty, 
)

from ..arch import ArchProperty
from ..array import ArrayProperty, ArrayGetSet
from ..fill import FillPanel, FillLouver, FillGlassPanes
from ..sizeoffset import SizeOffsetProperty, SizeOffsetGetSet


class DoorProperty(bpy.types.PropertyGroup, ArrayGetSet, SizeOffsetGetSet):
    arch: PointerProperty(type=ArchProperty)
    array: PointerProperty(type=ArrayProperty)
    size_offset: PointerProperty(type=SizeOffsetProperty)

    panel_fill: PointerProperty(type=FillPanel)
    louver_fill: PointerProperty(type=FillLouver)
    glass_fill: PointerProperty(type=FillGlassPanes)

    frame_thickness: FloatProperty(
        name="Frame Thickness",
        min=0.01,
        max=1.0,
        default=0.1,
        unit="LENGTH",
        description="Thickness of door Frame",
    )

    frame_depth: FloatProperty(
        name="Frame Depth",
        min=-1.0,
        max=1.0,
        step=1,
        default=0.0,
        unit="LENGTH",
        description="Depth of door Frame",
    )

    door_depth: FloatProperty(
        name="Door Depth",
        min=0.0,
        max=1.0,
        default=0.05,
        unit="LENGTH",
        description="Depth of door",
    )

    add_arch: BoolProperty(
        name="Add Arch", default=False, description="Add arch over door/window"
    )

    fill_types = [
        ("NONE", "None", "", 0),
        ("PANELS", "Panels", "", 1),
        ("GLASS_PANES", "Glass_Panes", "", 2),
        ("LOUVER", "Louver", "", 3),
    ]

    fill_type: EnumProperty(
        name="Fill Type",
        items=fill_types,
        default="NONE",
        description="Type of fill for door",
    )

    double_door: BoolProperty(
        name="Double Door", default=False, description="Double door"
    )

    def init(self, wall_dimensions):
        self["wall_dimensions"] = wall_dimensions
        self.size_offset.init(
            (self["wall_dimensions"][0] / self.count, self["wall_dimensions"][1]),
            default_size=(1.0, 1.5),
            default_offset=(0.0, 0.0),
        )
        self.arch.init(wall_dimensions[1] - self.size_offset.size.y)

    def draw(self, context, layout):
        box = layout.box()
        self.size_offset.draw(context, box)

        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, "frame_depth")
        row.prop(self, "frame_thickness")
        row = col.row(align=True)
        row.prop(self, "door_depth")

        self.array.draw(context, box)

        col = box.column(align=True)
        col.prop(self, "double_door")

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
            "PANELS": self.panel_fill,
            "LOUVER": self.louver_fill,
            "GLASS_PANES": self.glass_fill,
        }
        fill = fill_map.get(self.fill_type)
        if fill:
            fill.draw(box)

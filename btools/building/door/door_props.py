import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    PointerProperty,
)

from ...utils import get_scaled_unit
from ..arch import ArchProperty
from ..array import ArrayGetSet, ArrayProperty
from ..fill import FillGlassPanes, FillLouver, FillPanel
from ..sizeoffset import SizeOffsetGetSet, SizeOffsetProperty


class DoorProperty(bpy.types.PropertyGroup, ArrayGetSet, SizeOffsetGetSet):
    arch: PointerProperty(type=ArchProperty)
    array: PointerProperty(type=ArrayProperty)
    size_offset: PointerProperty(type=SizeOffsetProperty)

    panel_fill: PointerProperty(type=FillPanel)
    louver_fill: PointerProperty(type=FillLouver)
    glass_fill: PointerProperty(type=FillGlassPanes)

    add_bevel: BoolProperty(
        name="Bevel Frame",
        default=True,
        description="Chamfer frame edges for a manufactured profile",
    )
    bevel_width: FloatProperty(
        name="Bevel Width",
        min=get_scaled_unit(0.001),
        max=get_scaled_unit(0.01),
        default=get_scaled_unit(0.003),
        unit="LENGTH",
        description="Frame edge chamfer width",
    )
    add_casing: BoolProperty(
        name="Add Casing",
        default=False,
        description="Decorative trim ring around the opening",
    )
    casing_width: FloatProperty(
        name="Casing Width",
        min=get_scaled_unit(0.02),
        max=get_scaled_unit(0.15),
        default=get_scaled_unit(0.06),
        unit="LENGTH",
        description="Width of the trim ring on the wall",
    )
    casing_depth: FloatProperty(
        name="Casing Depth",
        min=get_scaled_unit(0.005),
        max=get_scaled_unit(0.05),
        default=get_scaled_unit(0.015),
        unit="LENGTH",
        description="How proud the casing stands from the wall",
    )
    add_hardware: BoolProperty(
        name="Add Handle",
        default=True,
        description="Add lever handle hardware to the door leaf",
    )
    handle_height: FloatProperty(
        name="Handle Height",
        min=get_scaled_unit(0.5),
        max=get_scaled_unit(1.5),
        default=get_scaled_unit(1.05),
        unit="LENGTH",
        description="Height of the handle from the floor",
    )
    handle_style: EnumProperty(
        name="Handle Style",
        items=[("LEVER", "Lever", "", 0), ("BAR_PULL", "Bar Pull", "", 1)],
        default="LEVER",
        description="Style of door handle",
    )
    frame_thickness: FloatProperty(
        name="Frame Thickness",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(1.0),
        default=get_scaled_unit(0.06),
        unit="LENGTH",
        description="Thickness of door Frame",
    )

    frame_depth: FloatProperty(
        name="Frame Depth",
        min=get_scaled_unit(-1.0),
        max=get_scaled_unit(1.0),
        step=1,
        default=get_scaled_unit(0.05),
        unit="LENGTH",
        description="Depth of door Frame",
    )

    door_depth: FloatProperty(
        name="Door Depth",
        min=get_scaled_unit(0.0),
        max=get_scaled_unit(1.0),
        default=get_scaled_unit(0.045),
        unit="LENGTH",
        description="Depth of door",
    )

    add_arch: BoolProperty(
        name="Add Arch", default=False, description="Add arch over door"
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
            default_size=(1.0, 1.8),
            default_offset=(0.0, 0.0),
            spread=self.array.spread,
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

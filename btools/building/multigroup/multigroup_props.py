import bpy
from bpy.props import (
    EnumProperty,
    BoolProperty,
    FloatProperty,
    StringProperty,
    PointerProperty,
)

from ..arch import ArchProperty
from ..array import ArrayGetSet, ArrayProperty
from ..fill import FillPanel, FillLouver, FillGlassPanes, FillBars
from ..sizeoffset import SizeOffsetProperty, SizeOffsetGetSet


class MultigroupProperty(bpy.types.PropertyGroup, ArrayGetSet, SizeOffsetGetSet):
    arch: PointerProperty(type=ArchProperty)
    array: PointerProperty(type=ArrayProperty)
    size_offset: PointerProperty(type=SizeOffsetProperty)

    panel_fill_door: PointerProperty(type=FillPanel)
    louver_fill_door: PointerProperty(type=FillLouver)
    glass_fill_door: PointerProperty(type=FillGlassPanes)

    bar_fill_window: PointerProperty(type=FillBars)
    panel_fill_window: PointerProperty(type=FillPanel)
    louver_fill_window: PointerProperty(type=FillLouver)
    glass_fill_window: PointerProperty(type=FillGlassPanes)

    frame_thickness: FloatProperty(
        name="Frame Thickness",
        min=0.01,
        max=1.0,
        default=0.1,
        unit="LENGTH",
        description="Thickness of door/window Frame",
    )

    frame_depth: FloatProperty(
        name="Frame Depth",
        step=1,
        min=-1.0,
        max=1.0,
        default=0.0,
        unit="LENGTH",
        description="Depth of door/window Frame",
    )

    window_height: FloatProperty(
        name="Window Height",
        step=1,
        min=0.1,
        max=1000.0,
        default=1.0,
        unit="LENGTH",
        description="Height of windows",
    )

    dw_depth: FloatProperty(
        name="Door/Window Depth",
        min=0.0,
        max=1.0,
        default=0.05,
        unit="LENGTH",
        description="Depth of door/window",
    )

    add_arch: BoolProperty(
        name="Add Arch", default=False, description="Add arch over door/window"
    )

    components: StringProperty(
        name="Components",
        default="dw",
        description="Components (Door and Windows): example: 'wdw' for a door surrounded by windows",
    )

    fill_types_door = [
        ("NONE", "None", "", 0),
        ("PANELS", "Panels", "", 1),
        ("GLASS_PANES", "Glass_Panes", "", 2),
        ("LOUVER", "Louver", "", 3),
    ]

    show_door_fill: BoolProperty(
        name="Show Door Fill", default=True, description="Show fill type properties for door"
    )

    fill_type_door: EnumProperty(
        name="Fill Type Door",
        items=fill_types_door,
        default="NONE",
        description="Type of fill for door",
    )

    fill_types_window = [
        ("NONE", "None", "", 0),
        ("PANELS", "Panels", "", 1),
        ("GLASS_PANES", "Glass_Panes", "", 2),
        ("LOUVER", "Louver", "", 3),
        ("BAR", "Bar", "", 4),
    ]

    show_window_fill: BoolProperty(
        name="Show Window Fill", default=True, description="Show fill type properties for window"
    )

    fill_type_window: EnumProperty(
        name="Fill Type Window",
        items=fill_types_window,
        default="NONE",
        description="Type of fill for window",
    )

    def init(self, wall_dimensions):
        self["wall_dimensions"] = wall_dimensions
        def_h = 1.8 if "d" in str(self.components) else 1.0
        self.size_offset.init(
            (self["wall_dimensions"][0] / self.count, self["wall_dimensions"][1]),
            default_size=(2.0, def_h),
            default_offset=(0.0, 0.0),
            spread=self.array.spread
        )
        if "d" not in str(self.components):
            self.arch.init(wall_dimensions[1] / 2 - self.size_offset.offset.y - self.size_offset.size.y / 2)
        else:
            self.arch.init(wall_dimensions[1] - self.size_offset.size.y)

    def draw(self, context, layout):
        box = layout.box()
        self.size_offset.draw(context, box)

        if "w" in str(self.components) and "d" in str(self.components):
            box.prop(self, "window_height")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Components")
        col.prop(self, "components", text="")
        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, "dw_depth")
        row = col.row(align=True)
        row.prop(self, "frame_depth")
        row.prop(self, "frame_thickness")

        self.array.draw(context, box)

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "add_arch")
        if self.add_arch:
            self.arch.draw(context, box)

        # -- draw fill types door
        box = layout.box()
        sp = box.split(factor=0.05, align=True)
        sp.prop(self, "show_door_fill", text="")
        sp.prop_menu_enum(self, "fill_type_door")

        fill_map = {
            "PANELS": self.panel_fill_door,
            "LOUVER": self.louver_fill_door,
            "GLASS_PANES": self.glass_fill_door,
        }
        fill = fill_map.get(self.fill_type_door)
        if fill and self.show_door_fill:
            fill.draw(box)


        # # -- draw fill types window
        box = layout.box()
        sp = box.split(factor=0.05, align=True)
        sp.prop(self, "show_window_fill", text="")
        sp.prop_menu_enum(self, "fill_type_window")

        fill_map = {
            "BAR": self.bar_fill_window,
            "PANELS": self.panel_fill_window,
            "LOUVER": self.louver_fill_window,
            "GLASS_PANES": self.glass_fill_window,
        }
        fill = fill_map.get(self.fill_type_window)
        if fill and self.show_window_fill:
            fill.draw(box)

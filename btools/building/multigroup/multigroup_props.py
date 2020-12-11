import bpy
from bpy.props import (
    EnumProperty,
    BoolProperty,
    FloatProperty,
    StringProperty,
    PointerProperty,
)

from ..fill import FillPanel, FillLouver, FillGlassPanes
from ..generic import ArchProperty, SizeOffsetProperty, CountProperty


class MultigroupProperty(bpy.types.PropertyGroup):
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
        description="Type of fill for door/window",
    )

    count: CountProperty
    arch: PointerProperty(type=ArchProperty)
    size_offset: PointerProperty(type=SizeOffsetProperty)

    panel_fill: PointerProperty(type=FillPanel)
    glass_fill: PointerProperty(type=FillGlassPanes)
    louver_fill: PointerProperty(type=FillLouver)

    def init(self, wall_dimensions):
        self["wall_dimensions"] = wall_dimensions
        def_h = 1.5 if "d" in str(self.components) else 1.0
        self.size_offset.init(
            (self["wall_dimensions"][0] / self.count, self["wall_dimensions"][1]),
            default_size=(2.0, def_h),
            default_offset=(0.0, 0.0),
        )
        if "d" not in str(self.components):
            self.arch.init(
                wall_dimensions[1] / 2 - self.size_offset.offset.y - self.size_offset.size.y / 2
            )
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

        col = box.column(align=True)
        col.prop(self, "count")

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "add_arch")
        if self.add_arch:
            self.arch.draw(context, box)

        box = layout.box()
        col = box.column(align=True)
        col.prop_menu_enum(self, "fill_type")

        # -- draw fill types
        fill_map = {
            "PANELS": self.panel_fill,
            "LOUVER": self.louver_fill,
            "GLASS_PANES": self.glass_fill,
        }
        fill = fill_map.get(self.fill_type)
        if fill:
            fill.draw(box)

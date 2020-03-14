import bpy
from bpy.props import FloatProperty, PointerProperty, EnumProperty

from ..generic import ArchProperty, ArrayProperty, SizeOffsetProperty
from ..fill import FillBars, FillLouver, FillGlassPanes


class WindowProperty(bpy.types.PropertyGroup):
    frame_thickness: FloatProperty(
        name="Frame Thickness",
        min=0.0,
        max=1.0,
        default=0.15,
        description="Thickness of window Frame",
    )

    frame_depth: FloatProperty(
        name="Frame Depth",
        min=0.0,
        max=0.5,
        default=0.0,
        description="Depth of window Frame",
    )

    window_depth: FloatProperty(
        name="Window Depth",
        min=0.0,
        max=0.5,
        default=0.05,
        description="Depth of window",
    )

    arch: PointerProperty(type=ArchProperty)
    array: PointerProperty(type=ArrayProperty)
    size_offset: PointerProperty(type=SizeOffsetProperty)

    fill_items = [
        ("NONE", "None", "", 0),
        ("BAR", "Bar", "", 1),
        ("LOUVER", "Louver", "", 2),
        ("GLASS_PANES", "Glass Panes", "", 3),
    ]
    fill_type: EnumProperty(
        name="Fill Type",
        items=fill_items,
        default="NONE",
        description="Type of fill for window",
    )

    bar_fill: PointerProperty(type=FillBars)
    louver_fill: PointerProperty(type=FillLouver)
    glass_fill: PointerProperty(type=FillGlassPanes)

    def has_arch(self):
        return self.arch.resolution > 0

    def init(self, wall_dimensions):
        self['wall_dimensions'] = wall_dimensions
        self.size_offset.init((self['wall_dimensions'][0]/self.array.count, self['wall_dimensions'][1]), default_size=(1.0, 1.0), default_offset=(0.0, 0.0))

    def draw(self, context, layout):
        self.size_offset.draw(context, layout)
        self.array.draw(context, layout)
        self.arch.draw(context, layout)

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "window_depth")
        row = col.row(align=True)
        row.prop(self, "frame_depth")
        row.prop(self, "frame_thickness")

        row = layout.row()
        row.prop_menu_enum(self, "fill_type")

        # -- draw fill types
        fill_map = {
            "BAR": self.bar_fill,
            "LOUVER": self.louver_fill,
            "GLASS_PANES": self.glass_fill,
        }
        fill = fill_map.get(self.fill_type)
        if fill:
            fill.draw(layout)

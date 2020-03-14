import bpy
from bpy.props import FloatProperty, EnumProperty, PointerProperty

from ..generic import ArchProperty, ArrayProperty, SizeOffsetProperty
from ..fill import FillPanel, FillLouver, FillGlassPanes


class DoorProperty(bpy.types.PropertyGroup):
    frame_thickness: FloatProperty(
        name="Frame Thickness",
        min=0.0,
        max=2.99,
        default=0.1,
        description="Thickness of door Frame",
    )

    frame_depth: FloatProperty(
        name="Frame Depth",
        min=0.0,
        max=100.0,
        default=0.0,
        step=1,
        description="Depth of door Frame",
    )

    door_depth: FloatProperty(
        name="Door Depth", min=0.0, max=0.5, default=0.05, description="Depth of door"
    )

    fill_items = [
        ("NONE", "None", "", 0),
        ("PANELS", "Panels", "", 1),
        ("GLASS_PANES", "Glass_Panes", "", 2),
        ("LOUVER", "Louver", "", 3),
    ]
    fill_type: EnumProperty(
        name="Fill Type",
        items=fill_items,
        default="NONE",
        description="Type of fill for door",
    )

    arch: PointerProperty(type=ArchProperty)
    array: PointerProperty(type=ArrayProperty)
    size_offset: PointerProperty(type=SizeOffsetProperty)

    panel_fill: PointerProperty(type=FillPanel)
    glass_fill: PointerProperty(type=FillGlassPanes)
    louver_fill: PointerProperty(type=FillLouver)

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
        col.prop(self, "door_depth")
        row = col.row(align=True)
        row.prop(self, "frame_thickness")
        row.prop(self, "frame_depth")

        row = layout.row()
        row.prop_menu_enum(self, "fill_type")

        # -- draw fill types
        fill_map = {
            "PANELS": self.panel_fill,
            "LOUVER": self.louver_fill,
            "GLASS_PANES": self.glass_fill,
        }
        fill = fill_map.get(self.fill_type)
        if fill:
            fill.draw(layout)

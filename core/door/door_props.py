import bpy
from bpy.props import FloatProperty, EnumProperty, PointerProperty, BoolProperty, IntProperty

from ..generic import ArchProperty, SizeOffsetProperty
from ..fill import FillPanel, FillLouver, FillGlassPanes


class DoorProperty(bpy.types.PropertyGroup):
    frame_thickness: FloatProperty(
        name="Frame Thickness",
        min=0.0,
        max=1.0,
        default=0.1,
        description="Thickness of door Frame",
    )

    frame_depth: FloatProperty(
        name="Frame Depth",
        min=0.0,
        max=1.0,
        default=0.0,
        step=1,
        description="Depth of door Frame",
    )

    door_depth: FloatProperty(
        name="Door Depth",
        min=0.0,
        max=1.0,
        default=0.05,
        description="Depth of door",
    )

    count: IntProperty(
        name="Count",
        min=1,
        max=100,
        default=1,
        description="Number of elements",
    )

    add_arch: BoolProperty(
        name="Add Arch",
        default=False,
        description="Add arch over door/window",
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
    size_offset: PointerProperty(type=SizeOffsetProperty)

    double_door: BoolProperty(
        name="Double Door",
        default=False,
        description="Double door",
    )

    panel_fill: PointerProperty(type=FillPanel)
    glass_fill: PointerProperty(type=FillGlassPanes)
    louver_fill: PointerProperty(type=FillLouver)

    def init(self, wall_dimensions):
        self['wall_dimensions'] = wall_dimensions
        self.size_offset.init((self['wall_dimensions'][0]/self.count, self['wall_dimensions'][1]), default_size=(1.0, 1.0), default_offset=(0.0, 0.0))

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

        col = box.column(align=True)
        col.prop(self, "count")

        col = box.column(align=True)
        col.prop(self, "double_door")

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
        }.get(self.fill_type)
        if fill:
            fill.draw(box)

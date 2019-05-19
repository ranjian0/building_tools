import bpy
from bpy.props import BoolProperty, FloatProperty, EnumProperty, PointerProperty

from ..generic import SizeOffsetProperty
from ..fill import FillPanel, FillLouver, FillGlassPanes


class DoorProperty(bpy.types.PropertyGroup):
    redo: BoolProperty()

    frame_thickness: FloatProperty(
        name="Frame Thickness",
        min=0.0,
        max=2.99,
        default=0.1,
        description="Thickness of inner door Frame",
    )

    frame_depth: FloatProperty(
        name="Frame Depth",
        min=0.0,
        max=100.0,
        default=0.05,
        step=1,
        description="Depth of inner door Frame",
    )

    has_double_door: BoolProperty(
        name="Double Door", default=False, description="If the door is split"
    )

    fill_items = [
        ("NONE", "None", "", 0),
        ("PANELS", "Panels", "", 1),
        ("GLASS PANES", "Glass Panes", "", 2),
        ("LOUVER", "Louver", "", 3),
    ]
    fill_type: EnumProperty(
        name="Fill Type",
        items=fill_items,
        default="NONE",
        description="Type of fill for door",
    )

    size_offset: PointerProperty(type=SizeOffsetProperty)

    panel_fill: PointerProperty(type=FillPanel)
    glass_fill: PointerProperty(type=FillGlassPanes)
    louver_fill: PointerProperty(type=FillLouver)

    def set_defaults(self):
        """ Helper function to make convinient property adjustments """
        if self.redo:
            return

        self.size_offset.size = (0.5, 1.0)
        self.redo = True

    def draw(self, context, layout):
        self.size_offset.draw(context, layout)

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "frame_thickness")
        col.prop(self, "frame_depth")

        box.prop(self, "has_double_door", toggle=True)

        row = layout.row()
        row.prop_menu_enum(self, "fill_type")

        # -- draw fill types
        fill_map = {
            "PANELS": self.panel_fill,
            "LOUVER": self.louver_fill,
            "GLASS PANES": self.glass_fill,
        }
        fill = fill_map.get(self.fill_type)
        if fill:
            fill.draw(layout)

import bpy
from bpy.props import *

from ..generic import SizeOffsetProperty
from ..fill import (
    FillPanel, FillLouver, FillGlassPanes
)


class DoorProperty(bpy.types.PropertyGroup):
    redo = BoolProperty()

    ft   = FloatProperty(
        name="Frame Thickness", min=0.0, max=2.99, default=0.1,
        description="Thickness of inner door Frame")

    fd   = FloatProperty(
        name="Frame Depth", min=0.0, max=100.0, default=0.05, step=1,
        description="Depth of inner door Frame")

    hdd  = BoolProperty(
        name='Double Door', default=False,
        description="If the door is split")

    fill_items = [
        ("NONE", "None", "", 0),
        ("PANELS", "Panels", "", 1),
        ("GLASS PANES", "Glass Panes", "", 2),
        ("LOUVER", "Louver", "", 3)

    ]
    fill_type = EnumProperty(
        name="Fill Type", items=fill_items, default="NONE",
        description="Type of fill for door")

    soff = PointerProperty(type=SizeOffsetProperty)

    panel_fill  = PointerProperty(type=FillPanel)
    glass_fill  = PointerProperty(type=FillGlassPanes)
    louver_fill = PointerProperty(type=FillLouver)

    def set_defaults(self):
        """ Helper function to make convinient property adjustments """
        if self.redo:
            return

        self.soff.size = (0.5, 1.0)
        self.redo = True


    def draw(self, context, layout):
        self.soff.draw(context, layout)

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, 'ft')
        col.prop(self, 'fd')

        box.prop(self, "hdd", toggle=True)

        row = layout.row()
        row.prop_menu_enum(self, "fill_type")

        # -- draw fill types
        fill_map = {
            "PANELS" : self.panel_fill,
            "LOUVER" : self.louver_fill,
            "GLASS PANES" : self.glass_fill,
        }
        fill = fill_map.get(self.fill_type)
        if fill:
            fill.draw(layout)

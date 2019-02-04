import bpy
from bpy.props import *

from ..generic import SizeOffsetProperty
from ..fill import (
        FillBars, FillLouver, FillGlassPanes
    )

class WindowProperty(bpy.types.PropertyGroup):
    ft   = FloatProperty(
        name="Frame Thickness", min=0.01, max=100.0, default=0.1,
        description="Thickness of window Frame")

    fd   = FloatProperty(
        name="Frame Depth", min=0.0, max=100.0, default=0.1,
        description="Depth of window Frame")

    soff = PointerProperty(type=SizeOffsetProperty)

    fill_itemss = [
        ("NONE", "None", "", 0),
        ("BAR", "Bar", "", 1),
        ("LOUVER", "Louver", "", 2),
        ("GLASS PANES", "Glass Panes", "", 3)
    ]
    fill_type  = EnumProperty(
        name="Fill Type", items=fill_itemss, default='NONE',
        description="Type of fill for window")

    bar_fill    = PointerProperty(type=FillBars)
    louver_fill = PointerProperty(type=FillLouver)
    glass_fill  = PointerProperty(type=FillGlassPanes)


    def draw(self, context, layout):
        self.soff.draw(context, layout)

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, 'ft')
        col.prop(self, 'fd')

        row = layout.row()
        row.prop_menu_enum(self, "fill_type")

        # -- draw fill types
        fill_map = {
            "BAR" : self.bar_fill,
            "LOUVER" : self.louver_fill,
            "GLASS PANES" : self.glass_fill,
        }
        fill = fill_map.get(self.fill_type)
        if fill:
            fill.draw(layout)

import bpy
from bpy.props import *

from ..generic import SizeOffsetProperty

class WindowProperty(bpy.types.PropertyGroup):

    fill_types = [
        ("BAR", "Bar", "", 0),
        ("PANE", "Pane", "", 1)
    ]
    fill       = EnumProperty(
        items=fill_types, default='BAR',
        description="Type of fill for window")

    ft         = FloatProperty(
        name="Frame Thickness", min=0.01, max=100.0, default=0.1,
        description="Thickness of window Frame")

    fd         = FloatProperty(
        name="Frame Depth", min=0.0, max=100.0, default=0.1,
        description="Depth of window Frame")

    px         = IntProperty(
        name="Horizontal Panes", min=0, max=100, default=1,
        description="Number of horizontal frames")

    py         = IntProperty(
        name="Vertical Panes", min=0, max=100, default=1,
        description="Number of vertical frames")

    pt         = FloatProperty(
        name="Pane Frame Thickness", min=0.01, max=100.0, default=0.1,
        description="Thickness of window pane frame")

    pd         = FloatProperty(
        name="Pane Frame Depth", min=0.01, max=100.0, default=0.01,
        description="Depth of window pane frame")

    soff       = PointerProperty(type=SizeOffsetProperty)

    def draw(self, context, layout):
        self.soff.draw(context, layout)

        row = layout.row()
        row.prop(self, "type", text="")

        box = layout.box()
        row = box.row(align=True)
        row.prop(self, 'fill', expand=True)

        col = box.column(align=True)
        col.prop(self, 'ft')
        col.prop(self, 'fd')

        col = box.column(align=True)
        row = col.row(align=True)

        txt_type = "Panes" if self.fill=='PANE' else "Bars"
        row.prop(self, 'px', text="Horizontal " + txt_type)
        row.prop(self, 'py', text="Vertical " + txt_type)

        txt = "Pane Thickness" if self.fill=='PANE' else 'Bar Thickness'
        col.prop(self, 'pt', text=txt)
        if self.fill == 'PANE':
            col.prop(self, 'pd')
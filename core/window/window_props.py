import bpy
from bpy.props import *

from ..generic import SizeOffsetProperty

class WindowProperty(bpy.types.PropertyGroup):
    win_types   = [("BASIC", "Basic", "", 0), ("ARCHED", "Arched", "", 1)]
    type        = EnumProperty(
        items=win_types, default='BASIC',
        description="Type of window")

    fill_type   = [("BAR", "Bar", "", 0), ("PANE", "Pane", "", 1)]
    fill        = EnumProperty(
        items=fill_type, default='BAR',
        description="Type of fill for window")

    ft          = FloatProperty(
        name="Frame Thickness", min=0.01, max=100.0, default=0.1,
        description="Thickness of window Frame")

    fd          = FloatProperty(
        name="Frame Depth", min=0.0, max=100.0, default=0.1,
        description="Depth of window Frame")

    px          = IntProperty(
        name="Horizontal Panes", min=0, max=100, default=1,
        description="Number of horizontal frames")

    py          = IntProperty(
        name="Vertical Panes", min=0, max=100, default=1,
        description="Number of vertical frames")

    pt          = FloatProperty(
        name="Pane Frame Thickness", min=0.01, max=100.0, default=0.1,
        description="Thickness of window pane frame")

    pd          = FloatProperty(
        name="Pane Frame Depth", min=0.01, max=100.0, default=0.01,
        description="Depth of window pane frame")

    ares        = IntProperty(
        name="Arc Resolution", min=0, max=1000, default=5,
        description="Number of segements for the arc")

    aoff        = FloatProperty(
        name="Arc Offset", min=0.01, max=1.0, default=0.5,
        description="How far arc is from top")

    aheight     = FloatProperty(
        name="Arc Height", min=0.01, max=100.0, default=0.5,
        description="Radius of the arc")

    adetail     = BoolProperty(
        name="Arc Detail", default=False,
        description="Whether to add detail to arc")

    dthick      = FloatProperty(
        name="Arc Detail Size", min=0.01, max=100.0, default=0.02,
        description="Size of arc details")

    ddepth      = FloatProperty(
        name="Arc Detail Depth", min=0.01, max=100.0, default=0.02,
        description="Depth of arc details")

    soff        = PointerProperty(type=SizeOffsetProperty)

    def draw(self, context, layout):
        self.soff.draw(context, layout, self)

        row = layout.row()
        row.prop(self, "type", text="")

        box = layout.box()
        if self.type == 'BASIC':
            pass

        elif self.type == 'ARCHED':
            # -- arch
            col = box.column(align=True)
            col.prop(self, 'ares')
            col.prop(self, 'aoff')
            col.prop(self, 'aheight')

            col = box.column(align=True)
            col.prop(self, 'adetail', toggle=True)
            if self.adetail:
                col.prop(self, 'dthick')
                col.prop(self, 'ddepth')

            # -- lower panes/bars
            box.separator()

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
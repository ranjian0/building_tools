import bpy
from bpy.props import *

from ..update import update_building
from ..generic import SplitProperty

class WindowProperty(bpy.types.PropertyGroup):
    win_types   = [("BASIC", "Basic", "", 0), ("ARCHED", "Arched", "", 1)]
    type        = EnumProperty(
        description="Type of window", items=win_types, default='BASIC',
        update=update_building)

    fill_type   = [("BAR", "Bar", "", 0), ("PANE", "Pane", "", 1)]
    fill        = EnumProperty(
        description="Type of fill for window",items=fill_type, default='BAR',
        update=update_building)

    ft          = FloatProperty(
        name="Frame Thickness", description="Thickness of window Frame", min=0.01, max=100.0, default=0.1,
        update=update_building)

    fd          = FloatProperty(
        name="Frame Depth", description="Depth of window Frame", min=0.0, max=100.0, default=0.1,
        update=update_building)

    px          = IntProperty(
        name="Horizontal Panes", description="Number of horizontal frames", min=0, max=100, default=1,
        update=update_building)

    py          = IntProperty(
        name="Vertical Panes", description="Number of vertical frames", min=0, max=100, default=1,
        update=update_building)

    pt          = FloatProperty(
        name="Pane Frame Thickness", description="Thickness of window pane frame", min=0.01, max=100.0, default=0.1,
        update=update_building)

    pd          = FloatProperty(
        name="Pane Frame Depth", description="Depth of window pane frame", min=0.01, max=100.0, default=0.01,
        update=update_building)

    ares        = IntProperty(
        name="Arc Resolution", description="Number of segements for the arc", min=0, max=1000, default=5,
        update=update_building)

    aoff        = FloatProperty(
        name="Arc Offset", description="How far arc is from top", min=0.01, max=1.0, default=0.5,
        update=update_building)

    aheight     = FloatProperty(
        name="Arc Height", description="Radius of the arc", min=0.01, max=100.0, default=0.5,
        update=update_building)

    adetail     = BoolProperty(
        name="Arc Detail", description="Whether to add detail to arc", default=False,
        update=update_building)

    dthick      = FloatProperty(
        name="Arc Detail Size", description="Size of arc details", min=0.01, max=100.0, default=0.02,
        update=update_building)

    ddepth      = FloatProperty(
        name="Arc Detail Depth", description="Depth of arc details", min=0.01, max=100.0, default=0.02,
        update=update_building)

    has_split   = BoolProperty(
        name="Add Split", description="Whether to split the window face", default=True,
        update=update_building)

    split       = PointerProperty(type=SplitProperty)

    mat_bar     = PointerProperty(type=bpy.types.Material,
        name="Bar Material", description="Material for window bars", update=update_building)

    mat_frame   = PointerProperty(type=bpy.types.Material,
        name="Frame Material", description="Material for window frame", update=update_building)

    mat_pane    = PointerProperty(type=bpy.types.Material,
        name="Pane Material", description="Material for window panes", update=update_building)

    mat_glass   = PointerProperty(type=bpy.types.Material,
        name="Glass Material", description="Material for window glass", update=update_building)

    def draw(self, context, layout):
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

        # -- draw split property
        self.split.draw(context, layout, self)

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "mat_frame")
        if self.fill == 'BAR':
            col.prop(self, "mat_bar")
        else:
            col.prop(self, "mat_pane")
        col.prop(self, "mat_glass")


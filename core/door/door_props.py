import bpy
from bpy.props import *

from ..generic import SizeOffsetProperty


class DoorProperty(bpy.types.PropertyGroup):
    ft     = FloatProperty(
        name="Frame Thickness", min=0.0, max=100.0, default=0.1,
        description="Thickness of inner door Frame")

    fd     = FloatProperty(
        name="Frame Depth", min=0.0, max=100.0, default=0.1, step=1,
        description="Depth of inner door Frame")

    px      = IntProperty(
        name="Horizontal Panes", min=0, max=100, default=1,
        description="Number of horizontal window panes")

    py      = IntProperty(
        name="Vertical Panes", min=0, max=100, default=1,
        description="Number of vertical window panes")

    pt      = FloatProperty(
        name="Pane Thickness", min=0.01, max=100.0, default=0.05,
        description="Thickness of window panes")

    pd      = FloatProperty(
        name="Pane Depth", min=0.01, max=100.0, default=0.01, step=1,
        description="Depth of window panes")

    offset  = FloatProperty(
        name="Pane Offset", min=-1.0, max=1.0, default=1.0,
        description="Offset of window panes")

    width   = FloatProperty(
        name="Pane Width", min=0.0, max=100.0, default=0.5,
        description="Width of window panes")

    gx      = IntProperty(
        name="Horizontal Grooves", min=0, max=100, default=1,
        description="Number of horizontal grooves")

    gy      = IntProperty(
        name="Vertical Grooves", min=0, max=100, default=1,
        description="Number of vertical grooves")

    gt      = FloatProperty(
        name="Groove Thickness", min=0.01, max=100.0, default=0.05,
        description="Thickness of groove")

    gd      = FloatProperty(
        name="Groove Depth", min=0.01, max=100.0, default=0.01, step=1,
        description="Depth of groove")

    gw      = FloatProperty(
        name="Groove Width", min=0.01, max=1.0, default=1.0,
        description="Width of grooves")

    goff    = FloatProperty(
        name="Groove Offset", min=-1.0, max=1.0, default=0.0,
        description="Offset of grooves")

    hdd     = BoolProperty(
        name='Double Door', default=False,
        description="If the door is split")

    grov    = BoolProperty(
        name='Grooved', default=False,
        description='Door has grooves')

    panned  = BoolProperty(
        name='Window Panes', default=False,
        description='Door has window panes')

    soff   = PointerProperty(type=SizeOffsetProperty)

    def draw(self, context, layout):
        self.soff.draw(context, layout)

        box = layout.box()
        box.prop(self, "hdd", toggle=True)

        col = box.column(align=True)
        col.prop(self, 'ft')
        col.prop(self, 'fd')

        # Panned
        box = layout.box()
        box.prop(self, 'panned', toggle=True)
        if self.panned:
            col = box.column(align=True)
            row = col.row(align=True)
            row.prop(self, 'px')
            row.prop(self, 'py')
            col.prop(self, 'pt')
            col.prop(self, 'pd')

            col = box.column(align=True)
            col.prop(self, 'offset')
            col.prop(self, 'width')

        # Groove
        box = layout.box()
        box.prop(self, 'grov', toggle=True)
        if self.grov:
            col = box.column(align=True)
            row = col.row(align=True)
            row.prop(self, 'gx')
            row.prop(self, 'gy')
            col.prop(self, 'gt')
            col.prop(self, 'gd')

            col = box.column(align=True)
            col.prop(self, 'goff')
            col.prop(self, 'gw')

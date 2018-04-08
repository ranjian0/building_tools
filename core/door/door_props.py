import bpy
from bpy.props import *

from ..generic import SplitProperty


class DoorProperty(bpy.types.PropertyGroup):
    oft     = FloatProperty(
        name="OuterFrame Thickness", min=0.0, max=100.0, default=0.0,
        description="Thickness of outer door Frame")

    ofd     = FloatProperty(
        name="OuterFrame Depth", min=0.0, max=100.0, default=0.0,
        description="Depth of outer door Frame")

    ift     = FloatProperty(
        name="InnerFrame Thickness", min=0.0, max=100.0, default=0.1,
        description="Thickness of inner door Frame",
        update=update_building)

    ifd     = FloatProperty(
        name="InnerFrame Depth", min=0.0, max=100.0, default=0.1, step=1,
        description="Depth of inner door Frame")

    # Window Panes
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

    # Grooves
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

    # Options
    hdd     = BoolProperty(
        name='Double Door', default=False,
        description="If the door is split")

    grov    = BoolProperty(
        name='Grooved', default=False,
        description='Door has grooves')

    panned  = BoolProperty(
        name='Window Panes', default=False,
        description='Door has window panes')

    # Door Split Options
    has_split   = BoolProperty(
        name="Add Split", default=True,
        description="Whether to split the door face")

    split   = PointerProperty(type=SplitProperty)

    mat_groov   = PointerProperty(type=bpy.types.Material,
        name="Groove Material", description="Material for door grooves")

    mat_frame   = PointerProperty(type=bpy.types.Material,
        name="Frame Material", description="Material for door frame")

    mat_pane    = PointerProperty(type=bpy.types.Material,
        name="Pane Material", description="Material for door panes")

    mat_glass   = PointerProperty(type=bpy.types.Material,
        name="Glass Material", description="Material for door glass")


    def draw(self, context, layout):
        box = layout.box()
        box.prop(self, "hdd", toggle=True)

        col = box.column(align=True)
        col.prop(self, 'oft')
        col.prop(self, 'ofd')

        col = box.column(align=True)
        col.prop(self, 'ift')
        col.prop(self, 'ifd')

        # Split
        self.split.draw(context, layout, self)

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

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "mat_frame")
        if self.panned:
            col.prop(self, "mat_pane")
        if self.grov:
            col.prop(self, "mat_groov")
        col.prop(self, "mat_glass")


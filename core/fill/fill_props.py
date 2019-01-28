import bpy
from bpy.props import *

class FillPanel(bpy.types.PropertyGroup):

    panel_x : IntProperty(
        name="Horizontal Panels", min=0, max=100, default=1,
        description="Number of horizontal panels")

    panel_y : IntProperty(
        name="Vertical Panels", min=0, max=100, default=1,
        description="Number of vertical panels")

    panel_b : FloatProperty(
        name="Panel Border", min=0.01, max=1.0, default=0.1,
        description="Border for panels")

    panel_t : FloatProperty(
        name="Panel Inset", min=0.01, max=1.0, default=0.1,
        description="Inset of each panel")

    panel_d : FloatProperty(
        name="Panel Depth", min=0.01, max=100.0, default=0.01, step=1,
        description="Depth of panels")


    def draw(self, layout):
        box = layout.box()

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, 'panel_x')
        row.prop(self, 'panel_y')
        col.prop(self, 'panel_b')
        col.prop(self, 'panel_t')
        col.prop(self, 'panel_d')

class FillGlassPanes(bpy.types.PropertyGroup):
    pane_x : IntProperty(
        name="Horizontal glass panes", min=0, max=100, default=1,
        description="Number of horizontal glass panes")

    pane_y : IntProperty(
        name="Vertical glass panes", min=0, max=100, default=1,
        description="Number of vertical glass panes")

    pane_t : FloatProperty(
        name="Glass Pane Thickness", min=0.01, max=100.0, default=0.05,
        description="Thickness of glass pane frames")

    pane_d : FloatProperty(
        name="Glass Pane Depth", min=0.01, max=100.0, default=0.01, step=1,
        description="Depth of glass panes")


    def draw(self, layout):
        box = layout.box()

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, 'pane_x')
        row.prop(self, 'pane_y')
        col.prop(self, 'pane_t')
        col.prop(self, 'pane_d')

class FillLouver(bpy.types.PropertyGroup):
    louver_count : IntProperty(
        name="Louver Count", min=0, max=1000, default=10,
        description="Number of louvers on to create face")

    louver_m     : FloatProperty(
        name="Louver Margin", min=0.0, max=100.0, default=0.1, step=1,
        description="Offset of louvers from face border")

    louver_d     : FloatProperty(
        name="Louver Depth", min=0.01, max=100.0, default=0.05, step=1,
        description="Depth of each louver")

    louver_b     : FloatProperty(
        name="Louver Border", min=0.0, max=1.0, default=0.01, step=1,
        description="Distance between louvers")

    def draw(self, layout):
        box = layout.box()
        box.prop(self, 'louver_m')

        col = box.column(align=True)
        col.prop(self, 'louver_count')
        col.prop(self, 'louver_d')
        col.prop(self, 'louver_b')



class FillBars(bpy.types.PropertyGroup):
    bar_x : IntProperty(
        name="Horizontal Bars", min=0, max=100, default=1,
        description="Number of horizontal bars")

    bar_y : IntProperty(
        name="Vertical Bars", min=0, max=100, default=1,
        description="Number of vertical bars")

    bar_t : FloatProperty(
        name="Bar Thickness", min=0.01, max=100.0, default=0.05,
        description="Thickness of bars")

    bar_d : FloatProperty(
        name="Bar Depth", min=0.01, max=100.0, default=0.05, step=1,
        description="Depth of bars")


    def draw(self, layout):
        box = layout.box()

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, 'bar_x')
        row.prop(self, 'bar_y')
        col.prop(self, 'bar_t')
        col.prop(self, 'bar_d')

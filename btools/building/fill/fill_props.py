import bpy
from bpy.props import IntProperty, FloatProperty, EnumProperty, PointerProperty


class FillPanel(bpy.types.PropertyGroup):

    panel_count_x: IntProperty(
        name="Horizontal Panels",
        min=0,
        max=100,
        default=1,
        description="Number of horizontal panels",
    )

    panel_count_y: IntProperty(
        name="Vertical Panels",
        min=0,
        max=100,
        default=1,
        description="Number of vertical panels",
    )

    panel_border_size: FloatProperty(
        name="Panel Border",
        min=0.01,
        max=1.0,
        default=0.1,
        unit="LENGTH",
        description="Border for panels",
    )

    panel_margin: FloatProperty(
        name="Panel Margin",
        min=0.01,
        max=1.0,
        default=0.05,
        unit="LENGTH",
        description="Margins of each panel",
    )

    panel_depth: FloatProperty(
        name="Panel Depth",
        step=1,
        min=0.01,
        max=100.0,
        default=0.01,
        unit="LENGTH",
        description="Depth of panels",
    )

    def draw(self, layout):
        box = layout.box()

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, "panel_count_x")
        row.prop(self, "panel_count_y")
        col.prop(self, "panel_border_size")
        col.prop(self, "panel_margin")
        col.prop(self, "panel_depth")


class FillGlassPanes(bpy.types.PropertyGroup):
    pane_count_x: IntProperty(
        name="Horizontal glass panes",
        min=0,
        max=10,
        default=1,
        description="Number of horizontal glass panes",
    )

    pane_count_y: IntProperty(
        name="Vertical glass panes",
        min=0,
        max=10,
        default=1,
        description="Number of vertical glass panes",
    )

    pane_margin: FloatProperty(
        name="Glass Pane Margin",
        min=0.01,
        max=1.0,
        default=0.1,
        unit="LENGTH",
        description="Margin of glass pane frames",
    )

    pane_depth: FloatProperty(
        name="Glass Pane Depth",
        min=0.0,
        max=0.1,
        default=0.03,
        step=0.1,
        unit="LENGTH",
        description="Depth of glass panes",
    )

    def draw(self, box):

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, "pane_count_x")
        row.prop(self, "pane_count_y")
        col.prop(self, "pane_margin")
        col.prop(self, "pane_depth")


class FillLouver(bpy.types.PropertyGroup):
    louver_count: IntProperty(
        name="Louver Count",
        min=0,
        max=100,
        default=10,
        description="Number of louvers on to create face",
    )

    louver_margin: FloatProperty(
        name="Louver Margin",
        step=1,
        min=0.001,
        max=100.0,
        default=0.1,
        unit="LENGTH",
        description="Offset of louvers from face border",
    )

    louver_depth: FloatProperty(
        name="Louver Depth",
        step=1,
        min=0.01,
        max=100.0,
        default=0.05,
        unit="LENGTH",
        description="Depth of each louver",
    )

    louver_border: FloatProperty(
        name="Louver Border",
        step=1,
        min=0.0,
        max=1.0,
        default=0.01,
        unit="LENGTH",
        description="Distance between louvers",
    )

    def draw(self, box):

        box.prop(self, "louver_margin")

        col = box.column(align=True)
        col.prop(self, "louver_count")
        col.prop(self, "louver_depth")
        col.prop(self, "louver_border")


class FillBars(bpy.types.PropertyGroup):
    bar_count_x: IntProperty(
        name="Horizontal Bars",
        min=0,
        max=100,
        default=1,
        description="Number of horizontal bars",
    )

    bar_count_y: IntProperty(
        name="Vertical Bars",
        min=0,
        max=100,
        default=1,
        description="Number of vertical bars",
    )

    bar_width: FloatProperty(
        name="Bar Width",
        min=0.01,
        max=100.0,
        default=0.1,
        unit="LENGTH",
        description="Width of bars"
    )

    bar_depth: FloatProperty(
        name="Bar Depth",
        step=1,
        min=0.01,
        max=1.0,
        default=0.04,
        unit="LENGTH",
        description="Depth of bars",
    )

    def draw(self, box):

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(self, "bar_count_x")
        row.prop(self, "bar_count_y")
        col.prop(self, "bar_width")
        col.prop(self, "bar_depth")


class FillProperty(bpy.types.PropertyGroup):
    fill_types = [
        ("PANELS", "Panels", "", 0),
        ("GLASS_PANES", "Glass_Panes", "", 1),
        ("LOUVER", "Louver", "", 2),
        ("BAR", "Bar", "", 3),
    ]

    fill_type: EnumProperty(
        name="Fill Type",
        items=fill_types,
        default="PANELS",
        description="Type of fill",
    )
    comp: EnumProperty(
        name="ComponentType",
        items=[("DOOR", "Door", "", 0), ("WINDOW", "Window", "", 1)],
        default="DOOR",
        description="Type of component",
    )

    panel_fill: PointerProperty(type=FillPanel)
    glass_fill: PointerProperty(type=FillGlassPanes)
    louver_fill: PointerProperty(type=FillLouver)
    bar_fill: PointerProperty(type=FillBars)

    def draw(self, context, layout):
        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "comp")
        col = box.column(align=True)
        col.prop(self, "fill_type")
        # -- draw fill types
        fill_map = {
            "PANELS": self.panel_fill,
            "LOUVER": self.louver_fill,
            "GLASS_PANES": self.glass_fill,
            "BAR": self.bar_fill,
        }
        fill = fill_map.get(self.fill_type)
        if fill:
            fill.draw(box)

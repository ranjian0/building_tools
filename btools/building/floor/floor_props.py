import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty

from ...utils import get_scaled_unit


class FloorProperty(bpy.types.PropertyGroup):
    floor_count: IntProperty(
        name="Floor Count", min=1, max=1000, default=1, description="Number of floors"
    )

    floor_height: FloatProperty(
        name="Floor Height",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(1000.0),
        default=get_scaled_unit(2.7),
        unit="LENGTH",
        description="Height of each floor",
    )

    add_slab: BoolProperty(
        name="Add Slab", default=True, description="Add slab between each floor"
    )

    slab_thickness: FloatProperty(
        name="Slab Thickness",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(1000.0),
        default=get_scaled_unit(0.2),
        unit="LENGTH",
        description="Thickness of each slab",
    )

    slab_outset: FloatProperty(
        name="Slab Outset",
        min=get_scaled_unit(0.0),
        max=get_scaled_unit(10.0),
        default=get_scaled_unit(0.1),
        unit="LENGTH",
        description="Outset of each slab",
    )

    wall_thickness: FloatProperty(
        name="Wall Thickness",
        min=get_scaled_unit(0.0),
        max=get_scaled_unit(1.0),
        default=get_scaled_unit(0.0),
        unit="LENGTH",
        description="Double-shell interior: offset the inner walls by this "
        "amount and add a floor per storey (0 keeps the single skin)",
    )

    add_cornice: BoolProperty(
        name="Add Cornice",
        default=False,
        description="Add a string-course cornice band along every slab line",
    )

    cornice_size: FloatProperty(
        name="Cornice Size",
        min=get_scaled_unit(0.02),
        max=get_scaled_unit(0.5),
        default=get_scaled_unit(0.12),
        unit="LENGTH",
        description="Projection of the cornice band past the slab edge",
    )

    add_columns: BoolProperty(
        name="Add Columns", default=False, description="Add Columns"
    )

    column_size: FloatProperty(
        name="Column Size",
        min=get_scaled_unit(0.0),
        max=get_scaled_unit(2.0),
        default=get_scaled_unit(0.0),
        unit="LENGTH",
        description="Column cross-section size (0 = follow 2x slab outset)",
    )

    add_column_base: BoolProperty(
        name="Column Bases",
        default=False,
        description="Add a wider base block at the foot of each plain column",
    )

    add_column_capital: BoolProperty(
        name="Column Capitals",
        default=False,
        description="Add a wider cap block at the head of each plain column",
    )

    column_cap_size: FloatProperty(
        name="Base/Cap Size",
        min=get_scaled_unit(1.05),
        max=get_scaled_unit(3.0),
        default=get_scaled_unit(1.4),
        subtype="FACTOR",
        description="Base/cap block size as a multiple of the column size",
    )

    column_cap_height: FloatProperty(
        name="Base/Cap Height",
        min=get_scaled_unit(0.02),
        max=get_scaled_unit(0.5),
        default=get_scaled_unit(0.08),
        unit="LENGTH",
        description="Height of the base and capital blocks",
    )

    add_decoration: BoolProperty(
        name="Add column decoration",
        default=False,
        description="Add columns decorations",
    )

    alternate_decoration: BoolProperty(
        name="Alternate decoration",
        default=False,
        description="Add columns decorations",
    )

    decoration_nb: IntProperty(
        name="Decoration Count",
        min=1,
        max=100,
        default=5,
        step=2,
        description="Number of decoration steps",
    )

    decoration_padding: FloatProperty(
        name="Decoration Padding",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(1.0),
        default=get_scaled_unit(0.01),
        unit="LENGTH",
        description="Space between decoration steps",
    )

    decoration_ratio: FloatProperty(
        name="Decoration Ration",
        min=get_scaled_unit(0.5),
        max=get_scaled_unit(3.0),
        default=get_scaled_unit(1),
        description="Space column decorations",
    )

    def draw(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, "floor_count")
        col.prop(self, "floor_height")

        # Slab
        row = layout.box()
        row.prop(self, "add_slab", text="Add slab ....")

        if self.add_slab == True:
            row.prop(self, "slab_thickness")
            row.prop(self, "slab_outset")

        # Interior
        row = layout.box()
        row.prop(self, "wall_thickness")

        # Cornice
        row = layout.box()
        row.prop(self, "add_cornice", text="Add cornice ....")
        if self.add_cornice:
            row.prop(self, "cornice_size")

        # Columns
        row = layout.box()
        row.prop(self, "add_columns", text="Add columns ....")

        if self.add_columns == True:
            row.prop(self, "add_decoration")
            if not self.add_decoration:
                row.prop(self, "column_size")
                row.prop(self, "add_column_base")
                row.prop(self, "add_column_capital")
                if self.add_column_base or self.add_column_capital:
                    row.prop(self, "column_cap_size")
                    row.prop(self, "column_cap_height")
            else:
                row.prop(self, "alternate_decoration")
                row.prop(self, "decoration_nb")
            row.prop(self, "decoration_padding")
            row.prop(self, "decoration_ratio")

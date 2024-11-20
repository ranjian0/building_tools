import bpy
from bpy.props import IntProperty, FloatProperty, BoolProperty
from ...utils import get_scaled_unit


class FloorProperty(bpy.types.PropertyGroup):
    floor_count: IntProperty(
        name="Floor Count", min=1, max=1000, default=1, description="Number of floors"
    )

    floor_height: FloatProperty(
        name="Floor Height",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(1000.0),
        default=get_scaled_unit(2.0),
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

    add_columns: BoolProperty(
        name="Add Columns", default=False, description="Add Columns"
    )

    add_decoration: BoolProperty(
        name="Add column decoration", default=False, description="Add columns decorations"
    )

    alternate_decoration: BoolProperty(
        name="Alternate decoration", default=False, description="Add columns decorations"
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
        max=get_scaled_unit(10.0),
        default=get_scaled_unit(0.01),
        unit="LENGTH",
        description="Space column decorations",
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

        
        #Slab
        row = layout.box()
        row.prop(self, "add_slab", text="Add slab ....")

        if self.add_slab == True:
            row.prop(self, "slab_thickness")
            row.prop(self, "slab_outset")

        #Columns
        row = layout.box()
        row.prop(self, "add_columns", text="Add columns ....")

        
        if self.add_columns == True:
            row.prop(self,"add_decoration")
            row.prop(self,"alternate_decoration")
            row.prop(self, "decoration_nb")
            row.prop(self, "decoration_padding")
            row.prop(self, "decoration_ratio")




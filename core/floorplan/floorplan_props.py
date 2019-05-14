import bpy
from bpy.props import *


class FloorplanProperty(bpy.types.PropertyGroup):
    fp_types = [
        ("RECTANGULAR", "Rectangular", "", 0),
        ("CIRCULAR", "Circular", "", 1),
        ("COMPOSITE", "Composite", "", 2),
        ("H-SHAPED", "H-Shaped", "", 3),
        ("RANDOM", "Random", "", 4),
    ]

    type: EnumProperty(
        items=fp_types, default="RECTANGULAR", description="Type of floorplan"
    )

    seed: IntProperty(
        name="Seed",
        min=0,
        max=10000,
        default=1,
        description="Seed for random generation",
    )

    width: FloatProperty(
        name="Width",
        min=0.01,
        max=100.0,
        default=2,
        description="Base Width of floorplan",
    )

    length: FloatProperty(
        name="Length",
        min=0.01,
        max=100.0,
        default=2,
        description="Base Length of floorplan",
    )

    radius: FloatProperty(
        name="Radius", min=0.1, max=100.0, default=1.0, description="Radius of circle"
    )

    segs: IntProperty(
        name="Segments",
        min=3,
        max=100,
        default=32,
        description="Number of segments in the circle",
    )

    tw1: FloatProperty(
        name="Tail Width",
        min=0.0,
        max=100.0,
        default=1,
        description="Width of floorplan segment",
    )

    tl1: FloatProperty(
        name="Tail Length",
        min=0.0,
        max=100.0,
        default=1,
        description="Length of floorplan segment",
    )

    tw2: FloatProperty(
        name="Tail Width 1",
        min=0.0,
        max=100.0,
        default=1,
        description="Width of floorplan segment",
    )

    tl2: FloatProperty(
        name="Tail Length 1",
        min=0.0,
        max=100.0,
        default=1,
        description="Length of floorplan segment",
    )

    tw3: FloatProperty(
        name="Tail Width 2",
        min=0.0,
        max=100.0,
        default=1,
        description="Width of floorplan segment",
    )

    tl3: FloatProperty(
        name="Tail Length 2",
        min=0.0,
        max=100.0,
        default=1,
        description="Length of floorplan segment",
    )

    tw4: FloatProperty(
        name="Tail Width 3",
        min=0.0,
        max=100.0,
        default=1,
        description="Width of floorplan segment",
    )

    tl4: FloatProperty(
        name="Tail Length 3",
        min=0.0,
        max=100.0,
        default=1,
        description="Length of floorplan segment",
    )

    cap_tris: BoolProperty(
        name="Cap Triangles",
        default=False,
        description="Set the fill type to triangles",
    )

    def draw(self, context, layout):
        row = layout.row()
        row.prop(self, "type", text="")

        box = layout.box()
        if self.type == "RECTANGULAR":
            col = box.column(align=True)
            col.prop(self, "width")
            col.prop(self, "length")

        elif self.type == "RANDOM":
            col = box.column(align=True)
            col.prop(self, "seed")
            col.prop(self, "width")
            col.prop(self, "length")

        elif self.type == "CIRCULAR":
            col = box.column(align=True)
            col.prop(self, "radius")
            col.prop(self, "segs")

            row = box.row()
            row.prop(self, "cap_tris", toggle=True)

        elif self.type == "COMPOSITE":
            row = box.row(align=True)
            row.prop(self, "width")
            row.prop(self, "length")

            col = box.column(align=True)
            col.prop(self, "tl1")
            col.prop(self, "tl2")
            col.prop(self, "tl3")
            col.prop(self, "tl4")

        elif self.type == "H-SHAPED":
            row = box.row(align=True)
            row.prop(self, "width")
            row.prop(self, "length")

            row = box.row(align=True)

            col = row.column(align=True)
            col.prop(self, "tw1")
            col.prop(self, "tw2")
            col.prop(self, "tw3")
            col.prop(self, "tw4")

            col = row.column(align=True)
            col.prop(self, "tl1")
            col.prop(self, "tl2")
            col.prop(self, "tl3")
            col.prop(self, "tl4")

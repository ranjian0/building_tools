import bpy
from bpy.props import EnumProperty, IntProperty, FloatProperty, BoolProperty

from ...utils import clamp


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
        default=4,
        unit="LENGTH",
        description="Base Width of floorplan",
    )

    length: FloatProperty(
        name="Length",
        min=0.01,
        max=100.0,
        default=4,
        unit="LENGTH",
        description="Base Length of floorplan",
    )

    random_extension_amount: BoolProperty(
        name="Random Extension Amount",
        default=True,
        description="Randomize the amount of extensions"
    )

    extension_amount: IntProperty(
        name="Extension Amount",
        min=1,
        max=4,
        default=1,
        description="Amount of extensions to generate",
    )

    radius: FloatProperty(
        name="Radius",
        min=0.1,
        max=100.0,
        default=1.0,
        unit="LENGTH",
        description="Radius of circle"
    )

    segments: IntProperty(
        name="Segments",
        min=3,
        max=100,
        default=32,
        description="Number of segments in the circle",
    )

    def get_segment_width(self, propname):
        return self.get(propname, 1.0)

    def set_segment_width(self, value, propname):
        """
        Clamp the segment width to less than default_width + base width
        ONLY for H-Shaped floorplan
        """
        default_width = 1.0
        maximum_width = default_width + self.width

        # -- calculate offsets of adjacent segments
        adjacent_prop = {
            "tw1" : "tw2",
            "tw2" : "tw1",
            "tw3" : "tw4",
            "tw4" : "tw3",
        }.get(propname)
        maximum_width += (default_width - self.get(adjacent_prop, 1.0))

        if self.type == "H-SHAPED":
            self[propname] = clamp(value, 0.0, maximum_width)
        else:
            self[propname] = value

    tw1: FloatProperty(
        name="Tail Width 1",
        min=0.0,
        max=100.0,
        unit="LENGTH",
        description="Width of floorplan segment",
        get=lambda self: self.get_segment_width("tw1"),
        set=lambda self, value: self.set_segment_width(value, "tw1"),
    )

    tl1: FloatProperty(
        name="Tail Length 1",
        min=0.0,
        max=100.0,
        default=1,
        unit="LENGTH",
        description="Length of floorplan segment",
    )

    tw2: FloatProperty(
        name="Tail Width 2",
        min=0.0,
        max=100.0,
        unit="LENGTH",
        description="Width of floorplan segment",
        get=lambda self: self.get_segment_width("tw2"),
        set=lambda self, value: self.set_segment_width(value, "tw2"),
    )

    tl2: FloatProperty(
        name="Tail Length 2",
        min=0.0,
        max=100.0,
        default=1,
        unit="LENGTH",
        description="Length of floorplan segment",
    )

    tw3: FloatProperty(
        name="Tail Width 3",
        min=0.0,
        max=100.0,
        unit="LENGTH",
        description="Width of floorplan segment",
        get=lambda self: self.get_segment_width("tw3"),
        set=lambda self, value: self.set_segment_width(value, "tw3"),
    )

    tl3: FloatProperty(
        name="Tail Length 3",
        min=0.0,
        max=100.0,
        default=1,
        unit="LENGTH",
        description="Length of floorplan segment",
    )

    tw4: FloatProperty(
        name="Tail Width 4",
        min=0.0,
        max=100.0,
        unit="LENGTH",
        description="Width of floorplan segment",
        get=lambda self: self.get_segment_width("tw4"),
        set=lambda self, value: self.set_segment_width(value, "tw4"),
    )

    tl4: FloatProperty(
        name="Tail Length 4",
        min=0.0,
        max=100.0,
        default=1,
        unit="LENGTH",
        description="Length of floorplan segment",
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
            col.prop(self, "random_extension_amount")

            if not self.random_extension_amount:
                col.prop(self, "extension_amount")

        elif self.type == "CIRCULAR":
            col = box.column(align=True)
            col.prop(self, "radius")
            col.prop(self, "segments")

        elif self.type == "COMPOSITE":
            row = box.row(align=True)
            row.prop(self, "width")
            row.prop(self, "length")

            col = box.column(align=True)
            col.prop(self, "tl1", text="Fan Length 1")
            col.prop(self, "tl2", text="Fan Length 2")
            col.prop(self, "tl3", text="Fan Length 3")
            col.prop(self, "tl4", text="Fan Length 4")

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

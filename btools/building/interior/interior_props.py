import bpy
from bpy.props import EnumProperty, FloatProperty, IntProperty

from ...utils import get_scaled_unit


class InteriorProperty(bpy.types.PropertyGroup):
    partition_modes = [
        ("TREEMAP", "Rooms", "", 0),
        ("SKELETON", "Corridor", "", 1),
    ]
    partition_mode: EnumProperty(
        name="Partition Mode",
        items=partition_modes,
        default="TREEMAP",
        description="How to subdivide the floor: squarified room grid or a "
        "medial-axis corridor wall",
    )

    room_count: IntProperty(
        name="Rooms",
        min=2,
        max=12,
        default=4,
        description="Number of rooms (treemap mode; equal areas)",
    )

    partition_thickness: FloatProperty(
        name="Partition Thickness",
        min=get_scaled_unit(0.01),
        max=get_scaled_unit(0.5),
        default=get_scaled_unit(0.1),
        unit="LENGTH",
        description="Thickness of partition walls",
    )

    partition_height: FloatProperty(
        name="Partition Height",
        min=get_scaled_unit(0.5),
        max=get_scaled_unit(10.0),
        default=get_scaled_unit(2.5),
        unit="LENGTH",
        description="Height of partition walls",
    )

    door_width: FloatProperty(
        name="Door Width",
        min=get_scaled_unit(0.5),
        max=get_scaled_unit(2.0),
        default=get_scaled_unit(0.9),
        unit="LENGTH",
        description="Width of door openings between rooms",
    )

    door_height: FloatProperty(
        name="Door Height",
        min=get_scaled_unit(1.0),
        max=get_scaled_unit(3.0),
        default=get_scaled_unit(2.1),
        unit="LENGTH",
        description="Height of door openings (a header fills the wall above)",
    )

    min_corridor: FloatProperty(
        name="Corridor Depth",
        min=get_scaled_unit(0.1),
        max=get_scaled_unit(5.0),
        default=get_scaled_unit(1.0),
        unit="LENGTH",
        description="Skeleton arcs deeper than this become corridor walls "
        "(corridor mode)",
    )

    inset: FloatProperty(
        name="Inset",
        min=get_scaled_unit(0.0),
        max=get_scaled_unit(2.0),
        default=get_scaled_unit(0.0),
        unit="LENGTH",
        description="Keep partitions this far inside the target face "
        "(use the building's wall thickness to meet the inner skin)",
    )

    def draw(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, "partition_mode", expand=True)

        box = layout.box()
        if self.partition_mode == "TREEMAP":
            col = box.column(align=True)
            col.prop(self, "room_count")
        else:
            col = box.column(align=True)
            col.prop(self, "min_corridor")

        col = box.column(align=True)
        col.prop(self, "inset")
        col.prop(self, "partition_thickness")
        col.prop(self, "partition_height")
        col.prop(self, "door_width")
        col.prop(self, "door_height")

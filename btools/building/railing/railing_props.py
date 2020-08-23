import bpy
from bpy.props import FloatProperty, EnumProperty, BoolProperty, PointerProperty


class PostFillProperty(bpy.types.PropertyGroup):
    size: FloatProperty(
        name="Size",
        min=0.01,
        max=100.0,
        default=0.05,
        unit="LENGTH",
        description="Size of each post",
    )

    density: FloatProperty(
        name="Density",
        min=0.0,
        max=1.0,
        default=0.5,
        description="Number of posts along each edge",
    )

    def draw(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "density")
        row.prop(self, "size")


class RailFillProperty(bpy.types.PropertyGroup):
    size: FloatProperty(
        name="Rail Size",
        min=0.01,
        max=100.0,
        default=0.05,
        unit="LENGTH",
        description="Size of each rail",
    )

    density: FloatProperty(
        name="Rail Density",
        min=0.0,
        max=1.0,
        default=0.4,
        description="Number of rails over each edge",
    )

    def draw(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "density")
        row.prop(self, "size")


class WallFillProperty(bpy.types.PropertyGroup):
    width: FloatProperty(
        name="Wall Width",
        min=0.0,
        max=100.0,
        default=0.075,
        unit="LENGTH",
        description="Width of each wall",
    )

    def draw(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "width")


class RailProperty(bpy.types.PropertyGroup):

    fill_types = [
        ("POSTS", "Posts", "", 0),
        ("RAILS", "Rails", "", 1),
        ("WALL", "Wall", "", 2),
    ]

    fill: EnumProperty(
        name="Fill Type",
        items=fill_types,
        default="POSTS",
        description="Type of railing",
    )

    corner_post_width: FloatProperty(
        name="Width",
        min=0.01,
        max=100.0,
        default=0.1,
        unit="LENGTH",
        description="Width of each corner post",
    )

    corner_post_height: FloatProperty(
        name="Height",
        min=0.01,
        max=100.0,
        default=0.7,
        unit="LENGTH",
        description="Height of each corner post",
    )

    has_corner_post: BoolProperty(
        name="Corner Posts",
        default=True,
        description="Whether the railing has corner posts",
    )

    offset: FloatProperty(
        name="Offset",
        default=0.05,
        unit="LENGTH",
        description="Railings offset",
    )

    post_fill: PointerProperty(type=PostFillProperty)
    rail_fill: PointerProperty(type=RailFillProperty)
    wall_fill: PointerProperty(type=WallFillProperty)

    show_extra_props: BoolProperty()
    bottom_rail: BoolProperty(
        name="Add Bottom Rail",
        default=True,
    )
    bottom_rail_offset: FloatProperty(
        name="Rail Offset",
        min=-1.0,
        max=1.0,
        default=0.0,
        unit="LENGTH",
        description="Offset of the bottom rail",
    )

    def draw(self, context, layout):
        row = layout.row()
        row.prop(self, "offset", text="Railing Offset")

        row = layout.row()
        row.prop_menu_enum(self, "fill", text=self.fill.title())

        {
            "POSTS" : self.post_fill,
            "RAILS" : self.rail_fill,
            "WALL"  : self.wall_fill
        }.get(self.fill).draw(context, layout)

        if self.fill in ["POSTS", "WALL"] and self.show_extra_props:
            row = layout.row(align=True)
            row.prop(self, "bottom_rail", toggle=True)
            row.prop(self, "bottom_rail_offset")

        layout.label(text="Corner Posts")
        row = layout.row(align=True)
        row.prop(self, "corner_post_width")
        row.prop(self, "corner_post_height")

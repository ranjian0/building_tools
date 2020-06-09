import bpy
from bpy.props import FloatProperty, EnumProperty, BoolProperty, PointerProperty


def get_density(self):
    return self.get("density", self.get("initial_density", 0.2))


def set_density(self, value):
    self["density"] = value


class PostFillProperty(bpy.types.PropertyGroup):
    size: FloatProperty(
        name="Size",
        min=0.01,
        max=100.0,
        default=0.05,
        description="Size of each post",
    )

    density: FloatProperty(
        name="Density",
        min=0.0,
        max=1.0,
        get=get_density,
        set=set_density,
        description="Number of posts along each edge",
    )

    def init(self, initial_density):
        self["initial_density"] = initial_density

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
        description="Size of each rail",
    )

    density: FloatProperty(
        name="Rail Density",
        min=0.0,
        max=1.0,
        default=0.3,
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
        description="Width of each corner post",
    )

    corner_post_height: FloatProperty(
        name="Height",
        min=0.01,
        max=100.0,
        default=0.7,
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
        description="Railings offset",
    )

    post_fill: PointerProperty(type=PostFillProperty)
    rail_fill: PointerProperty(type=RailFillProperty)
    wall_fill: PointerProperty(type=WallFillProperty)

    def init(self, stair_step_width=None, step_count=None):
        if stair_step_width and self.fill == "POSTS":
            if step_count > 1:
                initial_density = (self.post_fill.size * (step_count-1)) / (stair_step_width * step_count)
            else:
                initial_density = (self.post_fill.size - 0.001) / (2 * stair_step_width)  # just enough to have 0 post on stairs
            self.post_fill.init(initial_density=initial_density)

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

        layout.label(text="Corner Posts")
        row = layout.row(align=True)
        row.prop(self, "corner_post_width")
        row.prop(self, "corner_post_height")

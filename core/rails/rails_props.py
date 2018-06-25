import bpy
from bpy.props import *

class RailProperty(bpy.types.PropertyGroup):
    ps = FloatProperty(
        name="Post Size", min=0.01, max=100.0, default=0.05,
        description="Size of each post")

    pd = FloatProperty(
        name="Post Density", min=0.0, max=1.0, default=.3,
        description="Number of posts along each edge")

    rs = FloatProperty(
        name="Rail Size", min=0.01, max=100.0, default=0.05,
        description="Size of each rail")

    rd = FloatProperty(
        name="Rail Density", min=0.0, max=1.0, default=.3,
        description="Number of rails over each edge")

    ww = FloatProperty(
        name="Wall Width", min=0.0, max=100.0, default=0.075,
        description="Width of each wall")

    cpw = FloatProperty(
        name="Corner Post Width", min=0.01, max=100.0, default=0.15,
        description="Width of each corner post")

    cph = FloatProperty(
        name="Corner Post Height", min=0.01, max=100.0, default=0.7,
        description="Height of each corner post")

    hcp = BoolProperty(
        name="Corner Posts", default=True,
        description="Whether the railing has corner posts")

    expand = BoolProperty(
        name="Expand", default=False,
        description="Whether to expand fill type to extremes")

    has_decor = BoolProperty(
        name="Has Decor", default=False,
        description="Whether corner posts have decor")

    remove_colinear = BoolProperty(
        name="Remove Colinear", default=False,
        description="Whether to remove extra colinear posts")

    fill_types = [
        ("POSTS", "Posts", "", 0),
        ("RAILS", "Rails", "", 1),
        ("WALL", "Wall", "", 2)
    ]

    fill = EnumProperty(
        name="Fill Type", items=fill_types, default='POSTS',
        description="Type of railing")

    def draw(self, context, layout):

        row = layout.row()
        row.prop(self, "fill", text="")

        box = layout.box()
        if self.fill == 'POSTS':
            col = box.column(align=True)
            col.prop(self, 'pd')
            col.prop(self, 'ps')

            box1 = box.box()
            box1.label("Corner Posts")

            col = box1.column(align=True)
            col.prop(self, 'cpw')
            col.prop(self, 'cph')

            row = box1.row(align=True)
            row.prop(self, 'remove_colinear', toggle=True)
            row.prop(self, 'has_decor', toggle=True)

        elif self.fill == 'RAILS':
            col = box.column(align=True)
            col.prop(self, 'rd')
            col.prop(self, 'rs')
            col.prop(self, 'expand', text="Expand Rails", toggle=True)

            box1 = box.box()
            box1.label("Corner Posts")

            col = box1.column(align=True)
            col.prop(self, 'cpw')
            col.prop(self, 'cph')

            row = box1.row(align=True)
            row.prop(self, 'remove_colinear', toggle=True)
            row.prop(self, 'has_decor', toggle=True)

        elif self.fill == 'WALL':
            col = box.column(align=True)
            col.prop(self, 'ww')
            col.prop(self, 'expand', text="Expand Walls", toggle=True)

            box1 = box.box()
            box1.label("Corner Posts")

            col = box1.column(align=True)
            col.prop(self, 'cpw')
            col.prop(self, 'cph')

            row = box1.row(align=True)
            row.prop(self, 'remove_colinear', toggle=True)
            row.prop(self, 'has_decor', toggle=True)

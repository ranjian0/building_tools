import bpy
from bpy.props import *


class StairsProperty(bpy.types.PropertyGroup):
    step_count = IntProperty(
        name="Step Count", min=1, max=100, default=3,
        description="Number of steps")

    step_width = FloatProperty(
        name="Step Width", min=0.01, max=100.0, default=.5,
        description="Width of each step")

    scale = FloatProperty(
        name="Scale", min=0.0, max=1.0, default=0.0,
        description="Scale of the steps")

    bottom_faces = BoolProperty(
        name="Bottom Faces", default=True,
        description="Wether to delete bottom faces")

    def draw(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, 'step_count')
        col.prop(self, 'step_width')

        layout.prop(self, 'scale')
        layout.prop(self, 'bottom_faces', toggle=True)


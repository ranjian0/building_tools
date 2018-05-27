import bpy
from bpy.props import *

from ..generic import SizeOffsetProperty


class StairsProperty(bpy.types.PropertyGroup):
    step_count = IntProperty(
        name="Step Count", min=1, max=100, default=3,
        description="Number of steps")

    step_width = FloatProperty(
        name="Step Width", min=0.01, max=100.0, default=.5,
        description="Width of each step")

    landing_width  = FloatProperty(
        name="Landing Width", min=0.01, max=100.0, default=.5,
        description="Width of each stairs landing")

    landing = BoolProperty(
        name="Has Landing", default=True,
        description="Wether to stairs have a landing")

    soff = PointerProperty(type=SizeOffsetProperty)

    def draw(self, context, layout):
        self.soff.draw(context, layout)

        col = layout.column(align=True)
        col.prop(self, 'step_count')
        col.prop(self, 'step_width')

        box = layout.box()
        box.prop(self, 'landing', toggle=True)
        if self.landing:
            col = box.column()
            col.prop(self, 'landing_width')


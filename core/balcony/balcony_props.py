import bpy
from bpy.props import *

from ..generic import SizeOffsetProperty
from ..util_rail.rails_props import RailProperty

class BalconyProperty(bpy.types.PropertyGroup):
    width   = FloatProperty(
        name="Balcony Width", min=0.01, max=100.0, default=1.2,
        description="Width of balcony")

    railing = BoolProperty(
        name="Add Railing", default=True,
        description="Whether the balcony has railing")

    rail = PointerProperty(type=RailProperty)
    soff = PointerProperty(type=SizeOffsetProperty)

    def draw(self, context, layout):
        self.soff.draw(context, layout)

        row = layout.row()
        row.prop(self, 'width')

        box = layout.box()
        box.prop(self, 'railing', toggle=True)
        if self.railing:
            self.rail.draw(context, box)

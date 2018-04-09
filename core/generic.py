import bpy
from bpy.props import *


class SizeOffsetProperty(bpy.types.PropertyGroup):
    """ Convinience PropertyGroup used for reqular Quad Inset

    TODO: rename this, Split implies dividing in half
    TODO: rename properties to size and position
    TODO: Clamp amount factor to between 0.0 and 1.0. (0.0 - 3.0 is confusing)
    """
    size  = FloatVectorProperty(
        name="Size", min=.01, max=1.0, subtype='XYZ', size=2, default=(0.7, 0.7),
        description="Size of geometry")

    off     = FloatVectorProperty(
        name="Offset", min=-1000.0, max=1000.0, subtype='TRANSLATION', size=3, default=(0.0, 0.0, 0.0),
        description="How much to offset geometry")

    collapsed = BoolProperty(default=True)

    def draw(self, context, layout):
        box = layout.box()
        box.prop(self, 'collapsed', text="Size & Offset", toggle=True)

        if not self.collapsed:
            row = box.row(align=False)

            col = row.column(align=True)
            col.prop(self, 'size', slider=True)

            col = row.column(align=True)
            col.prop(self, 'off')
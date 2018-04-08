import bpy
from bpy.props import *


class SplitProperty(bpy.types.PropertyGroup):
    """ Convinience PropertyGroup used for reqular Quad Inset

    TODO: rename this, Split implies dividing in half
    TODO: rename properties to size and position
    TODO: Clamp amount factor to between 0.0 and 1.0. (0.0 - 3.0 is confusing)
    """
    amount  = FloatVectorProperty(
        name="Split Amount", description="How much to split geometry", min=.01, max=2.99,
        subtype='XYZ', size=2, default=(2.0, 2.7),
        update=update_building)

    off     = FloatVectorProperty(
        name="Split Offset", description="How much to offset geometry", min=-1000.0, max=1000.0,
        subtype='TRANSLATION', size=3, default=(0.0, 0.0, 0.0),
        update=update_building)

    collapsed = BoolProperty()

    def draw(self, context, layout, parent):
        box = layout.box()
        if parent.has_split:
            row = box.row(align=True)
            row.prop(parent, 'has_split', toggle=True)
            row.prop(self, 'collapsed', text="",
                icon='INLINK' if not self.collapsed else 'LINK')

            if not self.collapsed:
                col = box.column(align=True)
                col.prop(self, 'amount', slider=True)

                col = box.column(align=True)
                col.prop(self, 'off')
        else:
            box.prop(parent, 'has_split', toggle=True)

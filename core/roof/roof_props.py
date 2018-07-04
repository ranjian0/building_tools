import bpy
from bpy.props import *

class RoofProperty(bpy.types.PropertyGroup):
    roof_items = [
        ("FLAT", "Flat", "", 0),
        ("GABLE", "Gable", "", 1),
        ("HIP", "Hip", "", 2),
    ]
    type = EnumProperty(
        name="Roof Type", items=roof_items, default='FLAT',
        description="Type of roof to create")

    thick = FloatProperty(
        name="Thickness",  min=0.01, max=1000.0, default=.1,
        description="Thickness of roof hangs")

    outset = FloatProperty(
        name="Outset",  min=0.01, max=1000.0, default=.1,
        description="Outset of roof hangs")

    height = FloatProperty(
        name="Height",  min=0.01, max=1000.0, default=1,
        description="Height of entire roof")

    # o_types = [("LEFT", "Left", "", 0), ("RIGHT", "Right", "", 1), ]
    # orient = EnumProperty(description="Orientation of gable", items=o_types, default='LEFT')


    def draw(self, context, layout):
        layout.prop(self, 'type', text="")

        box = layout.box()
        if self.type == 'FLAT':
            col = box.column()
            col.prop(self, 'thick')
            col.prop(self, 'outset')

        elif self.type == 'GABLE':
            col = box.column()
            col.prop(self, 'thick')
            col.prop(self, 'outset')
            col.prop(self, 'height')

            # row = box.row(align=True)
            # row.prop(self, 'orient', expand=True)

        else:
            col = box.column()
            col.prop(self, 'thick')
            col.prop(self, 'outset')

            col.prop(self, 'height')

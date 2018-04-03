import bpy
from bpy.props import *

from ..update import update_building

class FloorplanProperty(bpy.types.PropertyGroup):
    fp_types = [
        ("RECTANGULAR", "Rectangular", "", 0),
        ("CIRCULAR", "Circular", "", 1),
        ("COMPOSITE", "Composite", "", 2),
        ("H-SHAPED", "H-Shaped", "", 3)
    ]

    type    = EnumProperty(
        description="Type of floorplan", items=fp_types, default='RECTANGULAR',
        update=update_building)

    width   = FloatProperty(
        name="Width", description="Base Width of floorplan", min=0.01, max=100.0, default=2,
        update=update_building)

    length  = FloatProperty(
        name="Length", description="Base Length of floorplan", min=0.01, max=100.0, default=2,
        update=update_building)

    radius  = FloatProperty(
        name="Radius", description="Radius of circle", min=0.1, max=100.0, default=1.0,
        update=update_building)

    segs    = IntProperty(
        name="Segments", description="Number of segments in the circle", min=3, max=100, default=32,
        update=update_building)

    tw      = FloatProperty(
        name="Tail Width", description="Width of floorplan segment", min=0.0, max=100.0, default=1,
        update=update_building)

    tl      = FloatProperty(
        name="Tail Length", description="Length of floorplan segment", min=0.0, max=100.0, default=1,
        update=update_building)

    tw1     = FloatProperty(
        name="Tail Width 1", description="Width of floorplan segment", min=0.0, max=100.0, default=1,
        update=update_building)

    tl1     = FloatProperty(
        name="Tail Length 1", description="Length of floorplan segment", min=0.0, max=100.0, default=1,
        update=update_building)

    tw2     = FloatProperty(
        name="Tail Width 2", description="Width of floorplan segment", min=0.0, max=100.0, default=1,
        update=update_building)

    tl2     = FloatProperty(
        name="Tail Length 2", description="Length of floorplan segment", min=0.0, max=100.0, default=1,
        update=update_building)

    tw3     = FloatProperty(
        name="Tail Width 3", description="Width of floorplan segment", min=0.0, max=100.0, default=1,
        update=update_building)

    tl3     = FloatProperty(
        name="Tail Length 3", description="Length of floorplan segment", min=0.0, max=100.0, default=1,
        update=update_building)

    cap_tris= BoolProperty(
        name='Cap Triangles', description='Set the fill type to triangles', default=False,
        update=update_building)

    def draw(self, context, layout):
        row = layout.row()
        row.prop(self, "type", text="")

        box = layout.box()
        if self.type == 'RECTANGULAR':
            col = box.column(align=True)
            col.prop(self, 'width')
            col.prop(self, 'length')

        elif self.type == 'CIRCULAR':
            col = box.column(align=True)
            col.prop(self, 'radius')
            col.prop(self, 'segs')

            row = box.row()
            row.prop(self, 'cap_tris', toggle=True)

        elif self.type == 'COMPOSITE':
            row = box.row(align=True)
            row.prop(self, 'width')
            row.prop(self, 'length')

            col = box.column(align=True)
            col.prop(self, 'tl')
            col.prop(self, 'tl1')
            col.prop(self, 'tl2')
            col.prop(self, 'tl3')

        elif self.type == 'H-SHAPED':
            row = box.row(align=True)
            row.prop(self, 'width')
            row.prop(self, 'length')

            row = box.row(align=True)

            col = row.column(align=True)
            col.prop(self, 'tw')
            col.prop(self, 'tw1')
            col.prop(self, 'tw2')
            col.prop(self, 'tw3')

            col = row.column(align=True)
            col.prop(self, 'tl')
            col.prop(self, 'tl1')
            col.prop(self, 'tl2')
            col.prop(self, 'tl3')

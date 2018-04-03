import bpy
from bpy.props import *

from .floor import FloorProperty
from .floorplan import FloorplanProperty

from .update import update_building

class PropertyProxy(bpy.types.PropertyGroup):
    property_items = [
        ("FLOORPLAN", "Floorplan", "", 0),
        ("FLOOR", "Floor", "", 1),
        ("WINDOW", "Window", "", 2),
        ("DOOR", "Door", "", 3)
    ]
    type    = EnumProperty(items=property_items)

    name    = StringProperty(default="Property")
    id      = IntProperty()


class SplitProperty(bpy.types.PropertyGroup):
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
            _icon = 'INLINK' if not self.collapsed else 'LINK'
            row.prop(self, 'collapsed', text="", icon=_icon)

            if not self.collapsed:
                col = box.column(align=True)
                col.prop(self, 'amount', slider=True)

                col = box.column(align=True)
                col.prop(self, 'off')
        else:
            box.prop(parent, 'has_split', toggle=True)


class BuildingProperty(bpy.types.PropertyGroup):

    floorplan   = PointerProperty(type=FloorplanProperty)
    floors      = PointerProperty(type=FloorProperty)
    # windows     = CollectionProperty(type=WindowProperty)
    # doors       = CollectionProperty(type=DoorProperty)
import bpy
from bpy.props import IntProperty, EnumProperty, BoolProperty, FloatVectorProperty


class SizeOffsetProperty(bpy.types.PropertyGroup):
    """ Convinience PropertyGroup used for regular Quad Inset (see window and door)"""

    size: FloatVectorProperty(
        name="Size",
        min=0.01,
        max=1.0,
        subtype="XYZ",
        size=2,
        default=(0.7, 0.7),
        description="Size of geometry",
    )

    offset: FloatVectorProperty(
        name="Offset",
        min=-1000.0,
        max=1000.0,
        subtype="TRANSLATION",
        size=3,
        default=(0.0, 0.0, 0.0),
        description="How much to offset geometry",
    )

    show_props: BoolProperty(default=False)

    def draw(self, context, layout):
        layout.prop(self, "show_props", text="Size & Offset", toggle=True)

        if self.show_props:
            box = layout.box()
            row = box.row(align=False)
            col = row.column(align=True)
            col.prop(self, "size", slider=True)

            col = row.column(align=True)
            col.prop(self, "offset")


class ArrayProperty(bpy.types.PropertyGroup):
    """ Convinience PropertyGroup used to array elements """

    count: IntProperty(
        name="Count", min=1, max=1000, default=3, description="Number of elements"
    )

    direction_items = [
        ("VERTICAL", "Vertical", "", 0),
        ("HORIZONTAL", "Horizontal", "", 1),
    ]
    direction: EnumProperty(
        name="Axis",
        items=direction_items,
        default="HORIZONTAL",
        description="Direction to array elements",
    )

    show_props: BoolProperty(default=False)

    def draw(self, context, layout):
        layout.prop(self, "show_props", text="Array Elements", toggle=True)

        if self.show_props:
            box = layout.box()
            col = box.column(align=True)
            # row = col.row(align=False)
            # row.prop(self, "direction", expand=True)
            row = col.row(align=False)
            row.prop(self, "count")


classes = (SizeOffsetProperty, ArrayProperty)


def register_generic():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_generic():
    for cls in classes:
        bpy.utils.unregister_class(cls)

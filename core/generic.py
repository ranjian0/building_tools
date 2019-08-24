import bpy
import bmesh
from bpy.props import (
    IntProperty,
    EnumProperty,
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
)

from ..utils import get_edit_mesh


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
        name="Count", min=1, max=1000, default=1, description="Number of elements"
    )

    show_props: BoolProperty(default=False)

    def draw(self, context, layout):
        layout.prop(self, "show_props", text="Array Elements", toggle=True)

        if self.show_props:
            box = layout.box()
            box.prop(self, "count")


class ArchProperty(bpy.types.PropertyGroup):
    """ Convinience PropertyGroup to create arched features """

    resolution: IntProperty(
        name="Arc Resolution",
        min=0,
        max=1000,
        default=0,
        description="Number of segements for the arc",
    )

    offset: FloatProperty(
        name="Arc Offset",
        min=0.01,
        max=1.0,
        default=0.5,
        description="How far arc is from top",
    )

    height: FloatProperty(
        name="Arc Height",
        min=0.01,
        max=100.0,
        default=0.5,
        description="Radius of the arc",
    )

    func_items = [("SINE", "Sine", "", 0), ("SPHERE", "Sphere", "", 1)]
    function: EnumProperty(
        name="Offset Function",
        items=func_items,
        default="SPHERE",
        description="Type of offset for arch",
    )

    show_props: BoolProperty(default=False)

    def draw(self, context, layout):
        layout.prop(self, "show_props", text="Arched", toggle=True)

        if self.show_props:
            box = layout.box()
            col = box.column(align=True)
            row = col.row(align=True)
            row.prop(self, "function", expand=True)
            col.prop(self, "resolution")
            col.prop(self, "offset")
            col.prop(self, "height")


class BTOOLS_UL_fmaps(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, icon, skip, _skip, _skip_):
        fmap = item
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(fmap, "name", text="", emboss=False, icon="FACE_MAPS")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class BTOOLS_OT_fmaps_clear(bpy.types.Operator):
    """Remove all empty face maps"""

    bl_idname = "btools.face_map_clear"
    bl_label = "Clear face maps"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == "MESH"

    def execute(self, context):
        obj = context.object
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)

        face_map = bm.faces.layers.face_map.active
        map_all_indices = {f.index for _, f in obj.face_maps.items()}
        map_used_indices = {f[face_map] for f in bm.faces}

        tag_remove = map_all_indices - map_used_indices
        tag_remove_maps = [obj.face_maps[idx] for idx in tag_remove]
        for fmap in tag_remove_maps:
            obj.face_maps.remove(fmap)

        bmesh.update_edit_mesh(me, True)
        return {"FINISHED"}


classes = (
    ArchProperty,
    ArrayProperty,
    BTOOLS_UL_fmaps,
    SizeOffsetProperty,
    BTOOLS_OT_fmaps_clear,
)


def register_generic():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_generic():
    for cls in classes:
        bpy.utils.unregister_class(cls)

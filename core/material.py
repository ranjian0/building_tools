import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    PointerProperty,
    CollectionProperty,
)

from ..utils import (
    bmesh_from_active_object,
    set_material_for_active_facemap,
)


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
    bl_label = "Clear empty face maps"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == "MESH"

    def execute(self, context):
        obj = context.object
        with bmesh_from_active_object(context) as bm:

            face_map = bm.faces.layers.face_map.active
            used_indices = {f[face_map] for f in bm.faces}
            all_indices = {f.index for f in obj.face_maps}
            tag_remove_indices = all_indices - used_indices

            # -- remove face maps
            tag_remove_maps = [obj.face_maps[idx] for idx in tag_remove_indices]
            for fmap in tag_remove_maps:
                obj.face_maps.remove(fmap)

            # -- remove facemap materials:
            for idx in reversed(list(tag_remove_indices)):
                obj.facemap_materials.remove(idx)

        return {"FINISHED"}


def update_facemap_material(self, context):
    """ Assign the updated material to all faces belonging to active facemap
    """
    set_material_for_active_facemap(self.material, context)
    return None


class FaceMapMaterial(bpy.types.PropertyGroup):
    """ Tracks materials for each facemap created for an object
    """

    material: PointerProperty(type=bpy.types.Material, update=update_facemap_material)

    auto_map: BoolProperty(
        name="Auto UV Mapping",
        default=True,
        description="Automatically UV Map faces belonging to active facemap.")

    mapping_methods = [
        ("UNWRAP", "Unwrap", "", 0),
        ("CUBE_PROJECTION", "Cube_Projection", "", 1),
    ]

    uv_mapping_method: EnumProperty(
        name="UV Mapping Method",
        items=mapping_methods,
        default="CUBE_PROJECTION",
        description="How to perform UV Mapping"
    )


classes = (
    FaceMapMaterial,
    BTOOLS_UL_fmaps,
    BTOOLS_OT_fmaps_clear,
)


def register_material():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.facemap_materials = CollectionProperty(type=FaceMapMaterial)


def unregister_material():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Object.facemap_materials

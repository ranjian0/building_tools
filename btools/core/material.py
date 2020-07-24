import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    PointerProperty,
    CollectionProperty,
)

from ..utils import (
    create_object_material,
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


def clear_empty_facemaps(context):
    """ Remove all facemaps that don't have any faces assigned
    """
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
        clear_empty_facemaps(context)
        return {"FINISHED"}


class BTOOLS_OT_create_facemap_material(bpy.types.Operator):
    """Create and assign a new material for the active facemap"""

    bl_idname = "btools.create_facemap_material"
    bl_label = "Assign New Material"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        active_facemap = obj.face_maps[obj.face_maps.active_index]
        mat = obj.facemap_materials[active_facemap.index].material
        return obj and obj.type == "MESH" and not mat

    def execute(self, context):
        obj = context.object
        active_facemap = obj.face_maps[obj.face_maps.active_index]

        # -- create new material
        mat = create_object_material(obj, "mat_" + active_facemap.name)
        mat_id = [idx for idx, m in enumerate(obj.data.materials) if m == mat].pop()
        obj.active_material_index = mat_id # make the new material active

        # -- assign to active facemap
        set_material_for_active_facemap(mat, context)
        obj.facemap_materials[active_facemap.index].material = mat
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
    BTOOLS_OT_create_facemap_material,
)


def register_material():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.facemap_materials = CollectionProperty(type=FaceMapMaterial)


def unregister_material():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Object.facemap_materials

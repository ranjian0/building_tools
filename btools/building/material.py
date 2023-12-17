import bpy
from bpy.props import (
    IntProperty,
    BoolProperty,
    EnumProperty,
    StringProperty,
    PointerProperty,
    CollectionProperty,
)

from ..utils import create_object_material, bmesh_from_active_object
from .materialgroup import (
    clear_empty_matgroups,
    set_material_for_active_matgroup,
    clear_material_for_active_matgroup,
)


class BTOOLS_UL_materials(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, icon, skip, _skip, _skip_):
        fmap = item
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(fmap, "name", text="", emboss=False, icon="FACE_MAPS")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class BTOOLS_OT_materials_clear(bpy.types.Operator):
    """Remove all material groups with no faces assigned"""

    bl_idname = "btools.materials_clear"
    bl_label = "Clear Empty Material Groups"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == "MESH"

    def execute(self, context):
        # -- remove all bt_materials that don't have any faces assigned
        clear_empty_matgroups(context)
        return {"FINISHED"}


class BTOOLS_OT_create_material(bpy.types.Operator):
    """Create and assign a new material for the active group"""

    bl_idname = "btools.create_material"
    bl_label = "Assign New Material"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        mat = obj.bt_materials[obj.bt_materials_active_index].material
        return obj and obj.type == "MESH" and not mat

    def execute(self, context):
        obj = context.object
        active_matgroup = obj.bt_materials[obj.bt_materials_active_index]

        # -- create new material
        mat = create_object_material(obj, "mat_" + active_matgroup.name)
        mat_id = [idx for idx, m in enumerate(obj.data.materials) if m == mat].pop()
        obj.active_material_index = mat_id  # make the new material active

        # -- assign to active matgroup
        set_material_for_active_matgroup(mat, context)
        active_matgroup.material = mat
        return {"FINISHED"}


class BTOOLS_OT_remove_material(bpy.types.Operator):
    """Remove the material from the active group"""

    bl_idname = "btools.remove_material"
    bl_label = "Remove Material"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        mat = obj.bt_materials[obj.bt_materials_active_index].material
        return obj and obj.type == "MESH" and mat

    def execute(self, context):
        obj = context.object
        active_matgroup = obj.bt_materials[obj.bt_materials_active_index]

        clear_material_for_active_matgroup(context)
        active_matgroup.material = None
        return {"FINISHED"}


class BTOOLS_OT_material_group_add(bpy.types.Operator):
    """Add a new material group to the active object"""

    bl_idname = "btools.material_group_add"
    bl_label = "Add Material Group"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == "MESH"

    def execute(self, context):
        obj = context.object
        mt = obj.bt_materials.add()
        mt.name = "mat_group_" + str(len(obj.bt_materials))
        mt.index = len(obj.bt_materials) - 1
        return {"FINISHED"}
    

class BTOOLS_OT_material_group_remove(bpy.types.Operator):
    """Remove the active material group"""

    bl_idname = "btools.material_group_remove"
    bl_label = "Add Material Group"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == "MESH" and len(obj.bt_materials)

    def execute(self, context):
        obj = context.object
        obj.bt_materials.remove(obj.bt_materials_active_index)
        return {"FINISHED"}


class BTOOLS_OT_material_group_assign(bpy.types.Operator):
    """Assign the selected faces to the active material group"""

    bl_idname = "btools.material_group_assign"
    bl_label = "Assign Faces to Group"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        matgroup = obj.bt_materials[obj.bt_materials_active_index]
        return matgroup

    def execute(self, context):
        obj = context.object
        active_matgroup = obj.bt_materials[obj.bt_materials_active_index]
        
        with bmesh_from_active_object(context) as bm:
            layer = bm.faces.layers.int.get(".bt_material_group_index")
            for face in bm.faces:
                if face.select:
                    face[layer] = active_matgroup.index
                    # -- assign material to face
                    if active_matgroup.material:
                        face.material_index = obj.data.materials.find(active_matgroup.material.name)
                    else:
                        face.material_index = 0
        
        return {"FINISHED"}
    

class BTOOLS_OT_material_group_remove_from(bpy.types.Operator):
    """Remove the selected faces from the active material group"""

    bl_idname = "btools.material_group_remove_from"
    bl_label = "Remove Faces from Group"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        matgroup = obj.bt_materials[obj.bt_materials_active_index]
        return matgroup

    def execute(self, context):
        with bmesh_from_active_object(context) as bm:
            layer = bm.faces.layers.int.get(".bt_material_group_index")
            for face in bm.faces:
                if face.select:
                    face[layer] = -1
                    # -- remove material from face
                    face.material_index = 0
        
        return {"FINISHED"}
    
    
class BTOOLS_OT_material_group_select(bpy.types.Operator):
    """Select all faces belonging to the active material group"""

    bl_idname = "btools.material_group_select"
    bl_label = "Select Faces in Group"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        matgroup = obj.bt_materials[obj.bt_materials_active_index]
        return matgroup

    def execute(self, context):
        obj = context.object
        active_group = obj.bt_materials[obj.bt_materials_active_index]
        with bmesh_from_active_object(context) as bm:
            layer = bm.faces.layers.int.get(".bt_material_group_index")
            for face in bm.faces:
                if face[layer] == active_group.index:
                    face.select = True
        
        return {"FINISHED"}
    

class BTOOLS_OT_material_group_deselect(bpy.types.Operator):
    """Deselect all faces belonging to the active material group"""

    bl_idname = "btools.material_group_deselect"
    bl_label = "Deselect Faces in Group"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        matgroup = obj.bt_materials[obj.bt_materials_active_index]
        return matgroup

    def execute(self, context):
        obj = context.object
        active_group = obj.bt_materials[obj.bt_materials_active_index]
        with bmesh_from_active_object(context) as bm:
            layer = bm.faces.layers.int.get(".bt_material_group_index")
            for face in bm.faces:
                if face[layer] == active_group.index:
                    face.select = False
        
        return {"FINISHED"}


def update_group_material(self, context):
    """Assign the updated material to all faces belonging to active group"""
    set_material_for_active_matgroup(self.material, context)
    return None

class BTMaterial(bpy.types.PropertyGroup):
    """Tracks materials for each face in an object"""
    index: IntProperty(default=-1)
    name: StringProperty(name="Name", default="")
    material: PointerProperty(type=bpy.types.Material, update=update_group_material)
    auto_map: BoolProperty(
        name="Auto UV Mapping",
        default=True,
        description="Automatically UV Map faces belonging to active group.",
    )

    mapping_methods = [
        ("UNWRAP", "Unwrap", "", 0),
        ("CUBE_PROJECTION", "Cube_Projection", "", 1),
    ]

    uv_mapping_method: EnumProperty(
        name="UV Mapping Method",
        items=mapping_methods,
        default="CUBE_PROJECTION",
        description="How to perform UV Mapping",
    )

classes = (
    BTMaterial,
    BTOOLS_UL_materials,
    BTOOLS_OT_materials_clear,
    BTOOLS_OT_create_material,
    BTOOLS_OT_remove_material,
    BTOOLS_OT_material_group_add,
    BTOOLS_OT_material_group_remove,
    BTOOLS_OT_material_group_assign,
    BTOOLS_OT_material_group_select,
    BTOOLS_OT_material_group_deselect,
    BTOOLS_OT_material_group_remove_from
)


def register_material():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.bt_materials = CollectionProperty(type=BTMaterial)
    bpy.types.Object.bt_materials_active_index = IntProperty(default=-1)


def unregister_material():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Object.bt_materials
    del bpy.types.Object.bt_materials_active_index

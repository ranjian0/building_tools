bl_info = {
    "name": "Building Tools",
    "author": "Ian Ichung'wa Karanja (ranjian0)",
    "version": (0, 9, 2),
    "blender": (2, 80, 0),
    "location": "View3D > Toolshelf > Building Tools",
    "description": "Building Creation Tools",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Mesh"
}

import bpy
from .core import register_core, unregister_core

# =======================================================
#
#           PANEL UI
#
# =======================================================


class PANEL_PT_mesh_tools(bpy.types.Panel):
    """UI panel for building operators and properties"""
    bl_label = "Mesh Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Building Tools'

    def draw(self, context):
        layout = self.layout

        # Draw Operators
        # ``````````````
        col = layout.column(align=True)
        col.operator("btools.add_floorplan")
        col.operator("btools.add_floors")

        row = col.row(align=True)
        row.operator("btools.add_window")
        row.operator("btools.add_door")

        row = col.row(align=True)
        row.operator("btools.add_railing")
        row.operator("btools.add_balcony")

        col.operator("btools.add_stairs")
        col.operator("btools.add_roof")

class MATERIAL_UL_matgroups(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        obj = data
        slot = item

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if obj:
                layout.prop(slot, "name", text="", emboss=False, icon_value=icon)
            else:
                layout.label(text="", translate=False, icon_value=icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

class PANEL_PT_material_tools(bpy.types.Panel):
    """UI panel for building operators and properties"""
    bl_label = "Material Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Building Tools'

    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and len(obj.mat_groups)

    def draw(self, context):
        layout = self.layout
        active_obj = context.object

        layout.label(text="Material Groups")
        layout.template_list("MATERIAL_UL_matgroups", "", active_obj, "mat_groups", active_obj, "mat_group_index")

        box = layout.box()
        current_mat = active_obj.mat_groups[active_obj.mat_group_index]
        box.prop(current_mat, "material", text="")

        row = box.row(align=True)
        row.prop(current_mat, "mat_options", expand=True)

        option = current_mat.mat_options
        col = box.column(align=True)
        if option == "BASE":
            col.prop(current_mat, "base_color", text="")
            col.prop(current_mat, "base_color_texture", text="")
        elif option == "SPECULAR":
            col.prop(current_mat, "specular", text="")
            col.prop(current_mat, "specular_texture", text="")
        elif option == "NORMAL":
            col.prop(current_mat, "normalmap_strength", text="")
            col.prop(current_mat, "normalmap_texture", text="")
        elif option == "METALLIC":
            col.prop(current_mat, "metallic", text="")
            col.prop(current_mat, "metallic_texture", text="")



# =======================================================
#
#           REGISTER
#
# =======================================================

classes = (
    PANEL_PT_mesh_tools,
    PANEL_PT_material_tools,
    MATERIAL_UL_matgroups,
)

def register():
    register_core()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    unregister_core()
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    # -- continuos updates with script watcher
    import os; os.system("clear")
    try:
        unregister()
    except Exception as e:
        print(e)
    finally:
        register()

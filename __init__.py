import bpy
from .core import register_core, unregister_core

bl_info = {
    "name": "Building Tools",
    "author": "Ian Ichung'wa Karanja (ranjian0)",
    "version": (0, 9, 5),
    "blender": (2, 80, 0),
    "location": "View3D > Toolshelf > Building Tools",
    "description": "Building Creation Tools",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Mesh",
}

# =======================================================
#
#           PANEL UI
#
# =======================================================


class PANEL_PT_mesh_tools(bpy.types.Panel):

    bl_label = "Mesh Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Building Tools"

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


class BTOOLS_UL_fmaps(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, icon, skip, _skip, _skip_):
        fmap = item
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(fmap, "name", text="", emboss=False, icon="FACE_MAPS")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class PANEL_PT_material_tools(bpy.types.Panel):

    bl_label = "Material Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Building Tools"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == "MESH"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Face Maps")

        ob = context.object
        facemap = ob.face_maps.active

        rows = 2
        if facemap:
            rows = 4

        row = layout.row()
        args = ob, "face_maps", ob.face_maps, "active_index"
        row.template_list("BTOOLS_UL_fmaps", "", *args, rows=rows)

        if ob.face_maps and (ob.mode == "EDIT" and ob.type == "MESH"):
            row = layout.row()

            sub = row.row(align=True)
            sub.operator("object.face_map_assign", text="Assign")
            sub.operator("object.face_map_remove_from", text="Remove")

            sub = row.row(align=True)
            sub.operator("object.face_map_select", text="Select")
            sub.operator("object.face_map_deselect", text="Deselect")


# =======================================================
#
#           REGISTER
#
# =======================================================

classes = (PANEL_PT_mesh_tools, PANEL_PT_material_tools, BTOOLS_UL_fmaps)


def register():
    register_core()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    unregister_core()
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    import os

    os.system("clear")

    try:
        unregister()
    except RuntimeError:
        pass
    finally:
        register()

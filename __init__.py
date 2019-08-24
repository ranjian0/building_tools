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

        ob = context.object
        facemap = ob.face_maps.active

        rows = 2
        if facemap:
            rows = 4

        if not len(ob.face_maps):
            return

        layout.label(text="Material Face Maps")

        row = layout.row()
        args = ob, "face_maps", ob.face_maps, "active_index"
        row.template_list("BTOOLS_UL_fmaps", "", *args, rows=rows)

        col = row.column(align=True)
        col.operator("object.face_map_add", icon='ADD', text="")
        col.operator("object.face_map_remove", icon='REMOVE', text="")

        if ob.face_maps and (ob.mode == "EDIT" and ob.type == "MESH"):
            row = layout.row()

            sub = row.row(align=True)
            sub.operator("object.face_map_assign", text="Assign")
            sub.operator("object.face_map_remove_from", text="Remove")

            sub = row.row(align=True)
            sub.operator("object.face_map_select", text="Select")
            sub.operator("object.face_map_deselect", text="Deselect")


classes = (PANEL_PT_mesh_tools, PANEL_PT_material_tools)


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

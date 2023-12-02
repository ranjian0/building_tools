import bpy
from .btools.building.register import register_building, unregister_building

bl_info = {
    "name": "Building Tools",
    "author": "Ian Karanja (ranjian0), Lucky Kadam (luckykadam), Marcus (MCrafterzz)",
    "version": (1, 0, 10),
    "blender": (2, 80, 0),
    "location": "View3D > Toolshelf > Building Tools",
    "description": "Building Creation Tools",
    "warning": "",
    "doc_url": "https://github.com/ranjian0/building_tools/wiki",
    "category": "Mesh",
}


class BTOOLS_PT_road_tools(bpy.types.Panel):

    bl_label = "Road Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Building Tools"

    def draw(self, context):
        layout = self.layout

        # Draw Operators
        # ``````````````
        col = layout.column(align=True)
        col.operator("btools.add_road")
        col.operator("btools.finalize_road")

        col = layout.column(align=True)
        col.operator("btools.add_array")
        col.operator("btools.finalize_array")


class BTOOLS_PT_building_tools(bpy.types.Panel):

    bl_label = "Building Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Building Tools"

    def draw(self, context):
        layout = self.layout

        # Draw Operators
        # ``````````````
        col = layout.column(align=True)
        col.operator("btools.add_floorplan")
        row = col.row(align=True)
        row.operator("btools.add_floors")
        row.operator("btools.add_roof")

        col = layout.column(align=True)
        col.operator("btools.add_balcony")
        col.operator("btools.add_stairs")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("btools.add_window")
        row.operator("btools.add_door")
        col.operator("btools.add_multigroup")
        col.operator("btools.add_fill")

        layout.separator(factor=1)
        col = layout.column(align=True)
        col.prop(context.scene, "btools_custom_object", text="")
        col.operator("btools.add_custom")

        layout.separator(factor=1)
        layout.operator("btools.remove_geom")


class BTOOLS_PT_material_tools(bpy.types.Panel):

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

        layout.label(text="Face Maps")

        row = layout.row()
        args = ob, "face_maps", ob.face_maps, "active_index"
        row.template_list("BTOOLS_UL_fmaps", "", *args, rows=rows)

        col = row.column(align=True)
        col.operator("object.face_map_add", icon="ADD", text="")
        col.operator("object.face_map_remove", icon="REMOVE", text="")
        col.separator()
        col.operator("btools.face_map_clear", icon="TRASH", text="")

        if ob.face_maps and (ob.mode == "EDIT" and ob.type == "MESH"):
            row = layout.row()

            sub = row.row(align=True)
            sub.operator("object.face_map_assign", text="Assign")
            sub.operator("object.face_map_remove_from", text="Remove")

            sub = row.row(align=True)
            sub.operator("object.face_map_select", text="Select")
            sub.operator("object.face_map_deselect", text="Deselect")

        if ob.face_maps:
            face_map_index = ob.face_maps.active_index
            if face_map_index < len(ob.facemap_materials):
                face_map_material = ob.facemap_materials[face_map_index]

                layout.label(text="UV Mapping")

                col = layout.column()
                row = col.row(align=True)
                row.alignment = "LEFT"
                row.prop(face_map_material, "auto_map", text="Auto")
                row.prop(face_map_material, "uv_mapping_method", text="")

                layout.label(text="Material")
                sp = layout.split(factor=0.8, align=True)
                sp.operator("btools.create_facemap_material")
                sp.operator("btools.remove_facemap_material", icon="PANEL_CLOSE", text="")
                layout.template_ID_preview(face_map_material, "material", hide_buttons=True)
            else:
                layout.label(text=("This facemap was corrupted by a destructive operation on the object."), icon="ERROR")


class BTOOLS_PT_PrefPanel(bpy.types.AddonPreferences):
    bl_idname = __name__

    # addon updater preferences
    auto_check_update : bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )

    updater_intrval_months : bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
    )
    updater_intrval_days : bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
    )
    updater_intrval_hours : bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23
    )
    updater_intrval_minutes : bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59
    )


    def draw(self, context):
        from . import addon_updater_ops
        addon_updater_ops.update_settings_ui(self, context)


classes = (BTOOLS_PT_building_tools, BTOOLS_PT_material_tools, BTOOLS_PT_PrefPanel)

register_ui, unregister_ui = bpy.utils.register_classes_factory(classes)

def register():
    try:
        from . import addon_updater_ops
        addon_updater_ops.register(bl_info)
    except ImportError:
        pass # XXX script_watcher dev environment

    register_building()
    register_ui()


def unregister():
    try:
        from . import addon_updater_ops
        addon_updater_ops.unregister()
    except ImportError:
        pass # XXX script_watcher dev environment

    unregister_building()
    unregister_ui()

if __name__ == "__main__":
    import os
    os.system("clear")

    # -- custom unregister for script watcher
    for tp in dir(bpy.types):
        if "BTOOLS_" in tp:
            bpy.utils.unregister_class(getattr(bpy.types, tp))

    register()

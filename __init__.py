bl_info = {
    "name": "Building Tools",
    "author": "Ian Ichung'wa Karanja (ranjian0)",
    "version": (0, 9, 3),
    "blender": (2, 80, 0),
    "location": "View3D > Toolshelf > Building Tools",
    "description": "Building Creation Tools",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Mesh",
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


# =======================================================
#
#           REGISTER
#
# =======================================================

classes = (PANEL_PT_mesh_tools,)


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
    import os

    os.system("clear")

    try:
        unregister()
    except RuntimeError:
        pass
    finally:
        register()

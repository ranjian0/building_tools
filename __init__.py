bl_info = {
    "name": "Building Tools",
    "author": "Ian Ichung'wa Karanja (ranjian0)",
    "version": (0, 0, 1),
    "blender": (2, 79, 0),
    "location": "View3D > Toolshelf > Building Tools",
    "description": "Building Creation Tools",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Cynthia"
}

import bpy
from .core import register_core, unregister_core

# =======================================================
#
#           PANEL UI
#
# =======================================================


class MeshGenerationPanel(bpy.types.Panel):
    """UI panel for building operators and properties"""

    bl_idname = "VIEW3D_PT_cynthia"
    bl_label = "Mesh Generation"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Building Tools'

    def draw(self, context):
        layout = self.layout
        active = context.object

        # Draw Operators
        # ``````````````
        col = layout.column(align=True)
        col.operator("cynthia.add_floorplan")
        col.operator("cynthia.add_floors")

        row = col.row(align=True)
        row.operator("cynthia.add_window")
        row.operator("cynthia.add_door")

        row = col.row(align=True)
        # row.operator("cynthia.add_railing")
        row.operator("cynthia.add_balcony")

        col.operator("cynthia.add_stairs")


# =======================================================
#
#           REGISTER
#
# =======================================================

def register():
    bpy.utils.register_class(MeshGenerationPanel)
    register_core()


def unregister():
    bpy.utils.unregister_class(MeshGenerationPanel)
    unregister_core()

if __name__ == "__main__":
    # -- continuos updates with script watcher
    import os; os.system("clear")
    try:
        unregister()
    except Exception as e:
        print("Unregister Failed")
    finally:
        register()

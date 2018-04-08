bl_info = {
    "name": "Cynthia",
    "author": "Ian Ichung'wa Karanja (ranjian0)",
    "version": (0, 0, 1),
    "blender": (2, 79, 0),
    "location": "View3D > Toolshelf > Cynthia",
    "description": "Building Generation Tools",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Add Mesh"
}

import bpy
from .core import register_core, unregister_core

# =======================================================
#
#           PANEL UI
#
# =======================================================


class CynthiaPanel(bpy.types.Panel):
    """UI panel for building operators and properties"""

    bl_idname = "VIEW3D_PT_cynthia"
    bl_label = "Cynthia Building Tools"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Cynthia Tools'

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
        row.operator("cynthia.add_railing")



# =======================================================
#
#           REGISTER
#
# =======================================================

def register():
    bpy.utils.register_class(CynthiaPanel)
    register_core()


def unregister():
    bpy.utils.unregister_class(CynthiaPanel)
    unregister_core()

if __name__ == "__main__":
    # -- continuos updates with script watcher
    import os; os.system("clear")
    try:
        unregister()
    except Exception as e:
        print(e)
    register()
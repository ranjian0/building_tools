from .version import VERSION
bl_info = {
    "name": "Building Tools",
    "author": "Ian Ichung'wa Karanja (ranjian0)",
    "version": VERSION,
    "blender": (2, 79, 0),
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


class MeshGenerationPanel(bpy.types.Panel):
    """UI panel for building operators and properties"""

    bl_label = "Mesh Generation"
    bl_idname = "VIEW3D_PT_btools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Building Tools'

    def draw(self, context):
        layout = self.layout
        active = context.object

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

def register():
    register_core()
    bpy.utils.register_class(MeshGenerationPanel)


def unregister():
    unregister_core()
    bpy.utils.unregister_class(MeshGenerationPanel)

if __name__ == "__main__":
    # -- continuos updates with script watcher
    import os; os.system("clear")
    try:
        unregister()
    except Exception as e:
        print(e)
    finally:
        register()

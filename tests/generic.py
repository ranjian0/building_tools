import bpy


class BTOOLS_PT_test_tools(bpy.types.Panel):
    bl_label = "Test Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Building Tools"

    def draw(self, context):
        layout = self.layout

        # Draw Operators
        # ``````````````
        col = layout.column(align=True)
        col.operator("btools.test_floorplan")
        col.operator("btools.test_floors")

        row = col.row(align=True)
        row.operator("btools.test_window")
        # row.operator("btools.add_door")

        # row = col.row(align=True)
        # row.operator("btools.add_railing")
        # row.operator("btools.add_balcony")

        # col.operator("btools.add_stairs")
        # col.operator("btools.add_roof")

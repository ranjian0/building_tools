import bpy
from .floorplan import Floorplan


class FloorplanOperator(bpy.types.Operator):
    """ Create a floorplan object """
    bl_idname = "cynthia.add_floorplan"
    bl_label = "Create Floorplan"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # Build the geometry
        fp = Floorplan()
        fp.build()

        # Add property list item
        # -- prop.id is optional, only useful for collectiontypes
        obj         = context.object
        prop        = obj.property_list.add()
        prop.id     = len(obj.property_list)
        prop.type   = "FLOORPLAN"
        prop.name   = "Floorplan Property"

        obj.property_index = len(obj.property_list)-1

        # Add flag to be used in update
        obj['has_floorplan'] = True

        return {'FINISHED'}


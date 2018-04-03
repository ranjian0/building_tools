import bpy
from .floor import Floor

class FloorOperator(bpy.types.Operator):
    """ Creates floors from active floorplan object """
    bl_idname = "cynthia.add_floors"
    bl_label = "Add Floors"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        # Build geometry
        floor = Floor()
        floor.build(context)

        # Add property list item
        # -- prop.id is optional, only useful for collectiontypes
        obj         = context.object
        prop        = obj.property_list.add()
        prop.id     = len(obj.property_list)
        prop.type   = "FLOOR"
        prop.name   = "Floor Property"

        obj.property_index = len(obj.property_list)-1

        # Add flag to be used in update
        obj['has_floor'] = True

        return {'FINISHED'}
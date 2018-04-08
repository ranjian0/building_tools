import bpy
from .floor import Floor
from .floor_props import FloorProperty

class FloorOperator(bpy.types.Operator):
    """ Creates floors from active floorplan object """
    bl_idname = "cynthia.add_floors"
    bl_label = "Add Floors"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=FloorProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        # Build geometry
        Floor.build(context, self.props)

        return {'FINISHED'}
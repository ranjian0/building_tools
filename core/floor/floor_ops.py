import bpy
from .floor import Floor
from .floor_props import FloorProperty

class FloorOperator(bpy.types.Operator):
    """ Creates floors from active floorplan object """
    bl_idname = "btools.add_floors"
    bl_label = "Add Floors"
    bl_options = {'REGISTER', 'UNDO'}

    props = bpy.props.PointerProperty(type=FloorProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        return Floor.build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)


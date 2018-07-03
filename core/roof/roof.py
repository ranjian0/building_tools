import bpy
import bmesh

class Roof:

    @classmethod
    def build(cls, context, props):
        return {'FINISHED'}
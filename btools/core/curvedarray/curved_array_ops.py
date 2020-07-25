import bpy

from .curved_array import CurvedArray


class BTOOLS_OT_add_curved_array(bpy.types.Operator):
    """Setup curved array
    """

    bl_idname = "btools.add_curved_array"
    bl_label = "Add Curved Array"
    bl_options = {"REGISTER", "PRESET"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        CurvedArray.build(context)
        return {"FINISHED"}


class BTOOLS_OT_finalize_curved_array(bpy.types.Operator):
    """Apply modifiers, remove curve and remove plane
    """

    bl_idname = "btools.finalize_curved_array"
    bl_label = "Finalize Curved Array"
    bl_options = {"REGISTER", "PRESET"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        CurvedArray.finalize_curved_array(context)
        return {"FINISHED"}

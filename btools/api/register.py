import bpy
from .ai_generate import BTOOLS_OT_ai_generate

classes = (
    BTOOLS_OT_ai_generate,
)


def register_api():
    for cls in classes:
        bpy.utils.register_class(cls)
        
def unregister_api():
    for cls in classes:
        bpy.utils.unregister_class(cls)
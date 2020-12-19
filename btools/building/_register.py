import bpy
from .arch import ArchProperty
from .array import ArrayProperty
from .sizeoffset import SizeOffsetProperty

from .customobj import register_custom, unregister_custom
from .material import register_material, unregister_material
from .removeobj import register_removeobj, unregister_removeobj

classes = (
    ArchProperty,
    ArrayProperty,
    SizeOffsetProperty,
)


def register_generic():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    register_custom()
    register_material()
    register_removeobj()


def unregister_generic():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    register_custom()
    register_material()
    register_removeobj()

import bpy

from .balcony import Balcony
from .balcony_ops import BalconyOperator
from .balcony_props import BalconyProperty

classes = (
    BalconyProperty, BalconyOperator
)

def register_balcony():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_balcony():
    for cls in classes:
        bpy.utils.unregister_class(cls)

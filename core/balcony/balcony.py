import bpy
import bmesh

from .balcony_types import make_balcony
from ...utils import (
    kwargs_from_props
    )

class Balcony:

    @classmethod
    def build(cls, context, props):
        """Use balcony types and properties to generate geomerty

        Args:
            context (bpy.context): blender context
            props   (bpy.types.PropertyGroup): BalconyProperty
        """
        make_balcony(**kwargs_from_props(props))
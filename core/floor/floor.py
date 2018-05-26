import bpy
import bmesh
from .floor_types import make_floors

from ...utils import (
    kwargs_from_props
    )


class Floor:

    @classmethod
    def build(cls, context, props):
        """Use floor types and properties to create geometry

        Args:
            context (bpy.context): blender context
            props   (bpy.types.PropertyGroup): FloorProperty
        """
        make_floors(**kwargs_from_props(props))

from .stairs_types import make_stairs
from ...utils import (
    kwargs_from_props
    )


class Stairs:

    @classmethod
    def build(self, context, props):
        """Use stair types and properties to generate geometry

        Args:
            context (bpy.context): blender context
            props   (bpy.types.PropertyGroup): StairsProperty
        """
        make_stairs(**kwargs_from_props(props))

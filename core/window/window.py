from .window_types import (
    make_window,
)

from ...utils import (
    kwargs_from_props
)

class Window:

    @classmethod
    def build(cls, context, props):
        """Use window types and properties to generate geometry

        Args:
            context (bpy.context): blender context
            props (bpy.types.PropertyGroup): WindowProperty
        """
        make_window(**kwargs_from_props(props))

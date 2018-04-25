import bpy
import bmesh
from .floor_types import flr_multistorey

from ...utils import (
    kwargs_from_props
    )


class Floor:

    @classmethod
    def build(cls, context, props):
        """ Build floorplan geomerty from properties """
        kwargs = kwargs_from_props(props)
        flr_multistorey(**kwargs)
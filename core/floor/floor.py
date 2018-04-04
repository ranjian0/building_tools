import bpy
from .floor_types import flr_multistorey

from ...utils import (
    bm_to_obj,
    bm_from_obj,
    kwargs_from_props
    )


class Floor:

    @classmethod
    def build(cls, context):
        """ Build floorplan geomerty from properties """

        # -- ensure that the mesh is a valid floorplan - (planar)
        if not cls.check_planar():
            return

        # -- create geometry
        props = context.object.building.floors
        flr_multistorey(**kwargs_from_props(props))

    @classmethod
    def check_planar(cls):
        """ Check to see in active mesh is planar """

        # -- get current object bmesh
        obj = bpy.context.object
        bm = bm_from_obj(obj)

        # -- check that all verts are on same z coordinate
        if len(set([v.co.z for v in bm.verts])) == 1:
            bm_to_obj(bm, obj)
            return True
        bm_to_obj(bm, obj)
        return False

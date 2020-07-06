import bpy
import bmesh
from .road_types import create_road, continuous_extrude
from ...utils import (
    link_obj,
    bm_to_obj,
    crash_safe,
    bm_from_obj,
    create_mesh,
    create_object,
    get_edit_mesh,
)


class Road:
    @classmethod
    @crash_safe
    def build(cls, context, prop):
        """ Create road object
        """
        name = "road_" + str("{:0>3}".format(len(bpy.data.objects) + 1))
        obj = create_object(name, create_mesh(name + "_mesh"))

        bm = bm_from_obj(obj)
        create_road(bm, prop)
        bm_to_obj(bm, obj)

        link_obj(obj)

        return obj

    @classmethod
    @crash_safe
    def extrude(cls, context, prop):
        times = prop.length / prop.interval
        me = get_edit_mesh()

        bm = bmesh.from_edit_mesh(me)
        continuous_extrude(bm, context, prop, bm.edges, times)
        bmesh.update_edit_mesh(me, True)

        return {"FINISHED"}

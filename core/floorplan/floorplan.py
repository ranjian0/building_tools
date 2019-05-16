import bpy
import bmesh

from .floorplan_types import (
    fp_rectangular,
    fp_circular,
    fp_composite,
    fp_hshaped,
    fp_random,
)

from ...utils import (
    link_obj,
    make_mesh,
    bm_to_obj,
    make_object,
    bm_from_obj,
    kwargs_from_props,
    create_default_materials,
)


class Floorplan:
    @classmethod
    def build(cls, context, prop):
        """Use floorplan types and properties to generate geometry

        Args:
            context (bpy.context): blender context
            props (bpy.types.PropertyGroup): FloorplanProperty
        """

        name = "building_" + str("{:0>3}".format(len(bpy.data.objects) + 1))
        obj = make_object(name, make_mesh(name + "_mesh"))
        bm = bm_from_obj(obj)

        if prop.type == "RECTANGULAR":
            fp_rectangular(bm, prop)

        elif prop.type == "CIRCULAR":
            fp_circular(bm, prop)

        elif prop.type == "COMPOSITE":
            fp_composite(bm, prop)

        elif prop.type == "H-SHAPED":
            fp_hshaped(bm, prop)

        elif prop.type == "RANDOM":
            fp_random(bm, prop)

        bm_to_obj(bm, obj)
        link_obj(obj)

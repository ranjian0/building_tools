import bpy
import bmesh

from .floorplan_types import (
    create_random_floorplan,
    create_hshaped_floorplan,
    create_circular_floorplan,
    create_composite_floorplan,
    create_rectangular_floorplan,
)

from ...utils import link_obj, make_mesh, bm_to_obj, make_object, bm_from_obj


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
            create_rectangular_floorplan(bm, prop)

        elif prop.type == "CIRCULAR":
            create_circular_floorplan(bm, prop)

        elif prop.type == "COMPOSITE":
            create_composite_floorplan(bm, prop)

        elif prop.type == "H-SHAPED":
            create_hshaped_floorplan(bm, prop)

        elif prop.type == "RANDOM":
            create_random_floorplan(bm, prop)

        bm_to_obj(bm, obj)
        link_obj(obj)

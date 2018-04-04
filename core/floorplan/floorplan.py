import bpy
import bmesh
from bmesh.types import BMVert
from mathutils import Vector

from .floorplan_types import (
    fp_rectangular,
    fp_circular,
    fp_composite,
    fp_hshaped
    )

from ...utils import (
    link_obj,
    condition,
    make_mesh,
    bm_to_obj,
    make_object,
    bm_from_obj,
    kwargs_from_props,
    )


class Floorplan:

    @classmethod
    def build(cls, update=False, _obj=None):
        """ Build the floorplan from given properties """

        # -- create the floorplan object
        obj = _obj if update else make_object('floorplan', make_mesh('fp_mesh'))
        building = obj.building

        # -- get bmesh representation of object
        bm = bm_from_obj(obj)

        # -- use properties to create geometry
        props   = building.floorplan
        kwargs  = kwargs_from_props(props)

        if props.type == 'RECTANGULAR':
            fp_rectangular(bm, **kwargs)

        elif props.type == 'CIRCULAR':
            fp_circular(bm, **kwargs)

        elif props.type == 'COMPOSITE':
            fp_composite(bm, **kwargs)

        elif props.type == 'H-SHAPED':
            print("Done")
            fp_hshaped(bm, **kwargs)

        # -- write bmesh back into object
        bm_to_obj(bm, obj)

        # -- link object to current scene
        if not update:
            link_obj(obj)

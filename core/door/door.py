from .door_types import (
    door_basic
    )

from ...utils import (
    kwargs_from_props,
    )


class Door:

    @classmethod
    def build(cls, context, facedata_list=[], update=False, id=0):
        """ Build door geomerty from selected faces """

        obj = context.object
        prop_id = id if update else obj.property_list[obj.property_index].id
        props = obj.building.doors[prop_id]

        cls.facedata_list = facedata_list
        cls.update = update

        door_basic(cls, **kwargs_from_props(props))

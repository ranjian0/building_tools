from .window_types import (
    win_basic,
    win_arched
    )

from ...utils import (
    kwargs_from_props
    )

class Window:

    @classmethod
    def build(cls, context, facedata_list=[], update=False, id=0):
        """ Create window geometry from selected faces """

        obj = context.object
        prop_id = id if update else obj.property_list[obj.property_index].id
        props = obj.building.windows[prop_id]

        cls.facedata_list = facedata_list
        cls.update = update

        kwargs = kwargs_from_props(props)
        if props.type == 'BASIC':
            win_basic(cls, **kwargs)
        elif props.type == 'ARCHED':
            win_arched(cls, **kwargs)

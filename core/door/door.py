from .door_types import (
    make_door
    )

from ...utils import (
    kwargs_from_props,
    )


class Door:

    @classmethod
    def build(cls, props):
        props.set_defaults()
        make_door(**kwargs_from_props(props))

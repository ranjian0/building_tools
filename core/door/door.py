from .door_types import (
    door_basic
    )

from ...utils import (
    kwargs_from_props,
    )


class Door:

    @classmethod
    def build(cls, context, props):
        door_basic(cls, **kwargs_from_props(props))

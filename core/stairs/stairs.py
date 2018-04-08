from .stairs_types import make_stairs_type1
from ...utils import (
    kwargs_from_props
    )


class Stairs:

    @classmethod
    def build(self, context, props):
        make_stairs_type1(**kwargs_from_props(props))
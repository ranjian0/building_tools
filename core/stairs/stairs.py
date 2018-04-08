from .stairs_types import make_stairs_type2
from ...utils import (
    kwargs_from_props
    )


class Stairs:

    @classmethod
    def build(self, context, props):
        make_stairs_type2(**kwargs_from_props(props))
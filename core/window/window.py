from .window_types import (
    win_basic,
    win_arched
    )

from ...utils import (
    kwargs_from_props
    )

class Window:

    @classmethod
    def build(cls, context, props):
        """ Create window geometry from selected faces """

        kwargs = kwargs_from_props(props)
        win_basic(cls, **kwargs)
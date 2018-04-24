from .window_types import (
    make_window,
)

from ...utils import (
    kwargs_from_props
)

class Window:

    @classmethod
    def build(cls, context, props):
        """ Create window geometry from selected faces """
        make_window(cls, **kwargs_from_props(props))
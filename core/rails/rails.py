import bpy
import bmesh

from .rails_types import make_railing
from ...utils import (
    get_edit_mesh,
    kwargs_from_props
    )

class Rails:

    @classmethod
    def build(cls, context, props):
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)

        edges = [e for e in edges if e.select]
        make_railing(bm, edges, **kwargs_from_props(props))

        bmesh.update_edit_mesh(me, True)

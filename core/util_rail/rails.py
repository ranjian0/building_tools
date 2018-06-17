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
        faces = [f for f in bm.faces if f.select]
        if faces:
            if not all([f.normal.z == 1.0 for f in faces]):
                return {'CANCELLED'}

        edges = [e for e in bm.edges if e.select]
        if edges:
            me = get_edit_mesh()
            bm = bmesh.from_edit_mesh(me)

            make_railing(bm, edges, **kwargs_from_props(props))
            bmesh.update_edit_mesh(me, True)
            return {'FINISHED'}
        return {'CANCELLED'}

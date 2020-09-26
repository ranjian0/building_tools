import bmesh

from .fill_types import add_fill
from ...utils import (
    crash_safe,
    is_rectangle,
    get_edit_mesh,
    verify_facemaps_for_object,
)


class Fill:
    @classmethod
    @crash_safe
    def build(cls, context, props):
        verify_facemaps_for_object(context.object)
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = cls.validate([face for face in bm.faces if face.select])
        if faces:
            if add_fill(bm, faces, props):
                bmesh.update_edit_mesh(me, True)
                return {"FINISHED"}

        bmesh.update_edit_mesh(me, True)
        return {"CANCELLED"}

    @classmethod
    def validate(cls, faces):
        """ Filter out invalid faces """
        # -- remove upward facing faces
        faces = list(filter(lambda f: abs(round(f.normal.z, 3)) == 0.0, faces))
        # -- remove non-rectangular faces
        faces = list(filter(lambda f: is_rectangle(f), faces))
        return faces

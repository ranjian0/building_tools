import bmesh

from .window_types import create_window
from ...utils import (
    FaceMap,
    crash_safe,
    is_rectangle,
    get_edit_mesh,
    add_facemap_for_groups,
    verify_facemaps_for_object,
)


class Window:
    @classmethod
    @crash_safe
    def build(cls, context, prop):
        verify_facemaps_for_object(context.object)
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = cls.validate([face for face in bm.faces if face.select])
        if faces:
            cls.add_window_facemaps()
            if create_window(bm, faces, prop):
                bmesh.update_edit_mesh(me, True)
                return {"FINISHED"}

        bmesh.update_edit_mesh(me, True)
        return {"CANCELLED"}

    @classmethod
    def add_window_facemaps(cls):
        groups = FaceMap.WINDOW, FaceMap.FRAME
        add_facemap_for_groups(groups)

    @classmethod
    def validate(cls, faces):
        """ Filter out invalid faces """
        # -- remove non-rectangular faces
        faces = list(filter(lambda f: is_rectangle(f), faces))
        # -- remove faces that are perpendicular to Z+
        faces = list(filter(lambda f: round(abs(f.normal.z), 2) != 1.0, faces))
        return faces

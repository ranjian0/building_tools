import bmesh

from .stairs_types import create_stairs
from ...utils import (
    FaceMap,
    crash_safe,
    get_edit_mesh,
    add_facemap_for_groups,
    verify_facemaps_for_object,
)


class Stairs:
    @classmethod
    @crash_safe
    def build(cls, context, prop):
        verify_facemaps_for_object(context.object)
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [f for f in bm.faces if f.select]

        if cls.validate(faces):
            cls.add_stairs_facemaps()
            if create_stairs(bm, faces, prop):
                bmesh.update_edit_mesh(me, True)
                return {"FINISHED"}

        bmesh.update_edit_mesh(me, True)
        return {"CANCELLED"}

    @classmethod
    def add_stairs_facemaps(cls):
        add_facemap_for_groups(FaceMap.STAIRS)

    @classmethod
    def validate(cls, faces):
        if faces:
            if not any([round(f.normal.z, 1) for f in faces]):
                return True
        return False

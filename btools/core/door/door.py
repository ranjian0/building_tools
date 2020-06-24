import bmesh

from .door_types import create_door
from ...utils import (
    FaceMap,
    crash_safe,
    get_edit_mesh,
    add_facemap_for_groups,
    verify_facemaps_for_object,
)


class Door:
    @classmethod
    @crash_safe
    def build(cls, context, props):
        verify_facemaps_for_object(context.object)
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [face for face in bm.faces if face.select]

        if cls.validate(faces):
            cls.add_door_facemaps()
            if create_door(bm, faces, props):
                bmesh.update_edit_mesh(me, True)
                return {"FINISHED"}
        return {"CANCELLED"}

    @classmethod
    def add_door_facemaps(cls):
        groups = FaceMap.DOOR, FaceMap.FRAME
        add_facemap_for_groups(groups)

    @classmethod
    def validate(cls, faces):
        if faces:
            if not any([round(f.normal.z, 1) for f in faces]):
                return True
        return False

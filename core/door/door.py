import bmesh

from .door_types import create_door
from ...utils import get_edit_mesh, FaceMap, add_facemap_for_groups


class Door:
    @classmethod
    def build(cls, props):
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [face for face in bm.faces if face.select]

        if cls.validate(faces):
            cls.add_door_facemaps()
            create_door(bm, faces, props)
            bmesh.update_edit_mesh(me, True)
            return {"FINISHED"}
        return {"CANCELLED"}

    @classmethod
    def add_door_facemaps(cls):
        groups = FaceMap.DOOR, FaceMap.DOOR_FRAMES
        add_facemap_for_groups(groups)

    @classmethod
    def validate(cls, faces):
        if faces:
            if not any([f.normal.z for f in faces]):
                return True
        return False

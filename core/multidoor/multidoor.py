import bmesh

from .multidoor_types import create_multidoor
from ...utils import get_edit_mesh, FaceMap, add_facemap_for_groups


class Multidoor:
    @classmethod
    def build(cls, props):
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [face for face in bm.faces if face.select]

        if cls.validate(faces):
            cls.add_multidoor_facemaps()
            if create_multidoor(bm, faces, props):
                bmesh.update_edit_mesh(me, True)
                return {"FINISHED"}
        return {"CANCELLED"}

    @classmethod
    def add_multidoor_facemaps(cls):
        groups = FaceMap.DOOR, FaceMap.WINDOW, FaceMap.FRAME
        add_facemap_for_groups(groups)

    @classmethod
    def validate(cls, faces):
        if faces:
            if not any([round(f.normal.z, 1) for f in faces]):
                return True
        return False

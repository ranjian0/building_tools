import bmesh

from .stairs_types import create_stairs
from ...utils import get_edit_mesh, FaceMap, add_facemap_for_groups


class Stairs:
    @classmethod
    def build(cls, context, prop):
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [f for f in bm.faces if f.select]

        if cls.validate(faces):
            cls.add_stairs_facemaps()
            create_stairs(bm, faces, prop)
            bmesh.update_edit_mesh(me, True)
            return {"FINISHED"}
        return {"CANCELLED"}

    @classmethod
    def add_stairs_facemaps(cls):
        add_facemap_for_groups(FaceMap.STAIRS)

    @classmethod
    def validate(cls, faces):
        if faces:
            if not any([f.normal.z for f in faces]):
                return True
        return False

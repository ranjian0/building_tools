import bmesh

from .roof_types import create_roof
from ...utils import (
    FaceMap,
    crash_safe,
    get_edit_mesh,
    add_facemap_for_groups,
    verify_facemaps_for_object,
)


class Roof:
    @classmethod
    @crash_safe
    def build(cls, context, props):
        verify_facemaps_for_object(context.object)
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [f for f in bm.faces if f.select]

        # XXX Fix normals if they are inverted(Z-)
        for f in faces:
            if f.normal.z < 0:
                f.normal_flip()

        if cls.validate(bm):
            cls.add_roof_facemaps()
            create_roof(bm, faces, props)
            bmesh.update_edit_mesh(me, True)
            return {"FINISHED"}

        bmesh.update_edit_mesh(me, True)
        return {"CANCELLED"}

    @classmethod
    def add_roof_facemaps(cls):
        add_facemap_for_groups(FaceMap.ROOF)

    @classmethod
    def validate(cls, bm):
        faces = [f for f in bm.faces if f.select]
        if faces:
            if all([round(f.normal.z, 1) for f in faces]):
                return True
        return False

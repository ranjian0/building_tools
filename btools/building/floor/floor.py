import bmesh

from .floor_types import create_floors
from ..material import clear_empty_facemaps
from ...utils import (
    select,
    FaceMap,
    crash_safe,
    get_edit_mesh,
    add_facemap_for_groups,
    verify_facemaps_for_object,
)


class Floor:
    @classmethod
    @crash_safe
    def build(cls, context, prop):
        verify_facemaps_for_object(context.object)

        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)

        # XXX Fix normals if they are inverted(Z-)
        for f in bm.faces:
            if f.normal.z < 0:
                f.normal_flip()

        if cls.validate(bm):
            cls.add_floor_facemaps(context, prop)
            selected_faces = [f for f in bm.faces if f.select]
            if selected_faces:
                create_floors(bm, selected_faces, prop)
                select(bm.faces, False)
            else:
                all_faces = [f for f in bm.faces]
                create_floors(bm, all_faces, prop)
            bmesh.update_edit_mesh(me, True)
            return {"FINISHED"}

        bmesh.update_edit_mesh(me, True)
        return {"CANCELLED"}

    @classmethod
    def add_floor_facemaps(cls, context, prop):
        clear_empty_facemaps(context)
        groups = FaceMap.WALLS, FaceMap.ROOF
        if prop.add_slab:
            groups += (FaceMap.SLABS,)
        if prop.add_columns:
            groups += (FaceMap.COLUMNS,)
        add_facemap_for_groups(groups)

    @classmethod
    def validate(cls, bm):
        if any([f for f in bm.faces if f.select]):
            selection = [f for f in bm.faces if f.select]
            if len({round(v.co.z, 4) for f in selection for v in f.verts}) == 1:
                return True
        elif len({round(v.co.z, 4) for v in bm.verts}) == 1:
            return True
        return False

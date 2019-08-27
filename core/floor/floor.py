import bmesh
from .floor_types import create_floors

from ...utils import (
    select,
    FaceMap,
    get_edit_mesh,
    add_facemap_for_groups,
    verify_facemaps_for_object,
)


class Floor:
    @classmethod
    def build(cls, context, prop):
        verify_facemaps_for_object(context.object)

        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)

        if cls.validate(bm):
            cls.add_floor_facemaps()
            if any([f for f in bm.faces if f.select]):
                create_floors(bm, None, prop)
                select(bm.faces, False)
            else:
                edges = [e for e in bm.edges if e.is_boundary]
                create_floors(bm, edges, prop)
            bmesh.update_edit_mesh(me, True)
            return {"FINISHED"}
        return {"CANCELLED"}

    @classmethod
    def add_floor_facemaps(cls):
        groups = FaceMap.SLABS, FaceMap.WALLS
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

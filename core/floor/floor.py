import bmesh
from .floor_types import create_floors

from ...utils import select, get_edit_mesh, FaceMap


class Floor:
    @classmethod
    def build(cls, context, prop):
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)

        if cls.validate(bm):
            cls.set_facemaps(context.object)
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
    def set_facemaps(cls, obj):
        fmaps = FaceMap.SLABS, FaceMap.WALLS
        for fm in fmaps:
            obj.face_maps.new(name=fm.name.lower())

    @classmethod
    def validate(cls, bm):
        if any([f for f in bm.faces if f.select]):
            selection = [f for f in bm.faces if f.select]
            if len({round(v.co.z, 4) for f in selection for v in f.verts}) == 1:
                return True
        elif len({round(v.co.z, 4) for v in bm.verts}) == 1:
            return True
        return False

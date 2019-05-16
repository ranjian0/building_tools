import bpy
import bmesh
from .floor_types import create_floors

from ...utils import select, get_edit_mesh


class Floor:
    has_mat_groups = False

    @classmethod
    def build(cls, context, prop):
        """Use floor types and properties to create geometry

        Args:
            context (bpy.context): blender context
            prop   (bpy.types.PropertyGroup): FloorProperty
        """

        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)

        if cls.validate(bm):
            if any([f for f in bm.faces if f.select]):
                create_floors(bm, None, prop)
            else:
                edges = [e for e in bm.edges if e.is_boundary]
                create_floors(bm, edges, prop)
            bmesh.update_edit_mesh(me, True)
            return {"FINISHED"}
        return {"CANCELLED"}

    @classmethod
    def validate(cls, bm):
        """ Validate input if any """
        if len(list({v.co.z for v in bm.verts})) == 1:
            return True
        elif any([f for f in bm.faces if f.select]):
            return True
        return False

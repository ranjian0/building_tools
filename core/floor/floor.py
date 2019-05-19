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
            prop (bpy.types.PropertyGroup): FloorProperty

        Returns:
            set(str): operator exit state
        """

        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)

        if cls.validate(bm):
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
    def validate(cls, bm):
        """Validate input if any

        Args:
            bm (bmesh.types.BMesh): bmesh of editmode object

        Returns:
            bool: whethed the current edit mesh is valid
        """
        if any([f for f in bm.faces if f.select]):
            selection = [f for f in bm.faces if f.select]
            if len({round(v.co.z, 4) for f in selection for v in f.verts}) == 1:
                return True
        elif len({round(v.co.z, 4) for v in bm.verts}) == 1:
            return True
        return False

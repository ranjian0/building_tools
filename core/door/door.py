import bmesh

from .door_types import create_door
from ...utils import get_edit_mesh


class Door:
    @classmethod
    def build(cls, props):
        """Use door types and properties to generate geometry

        Args:
            props (bpy.types.PropertyGroup): DoorProperty

        Returns:
            set(str): Operator exit state
        """
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [face for face in bm.faces if face.select]

        if cls.validate(faces):
            create_door(bm, faces, props)
            bmesh.update_edit_mesh(me, True)
            return {"FINISHED"}
        return {"CANCELLED"}

    @classmethod
    def validate(cls, faces):
        """Ensure user has appropriate selection if any

        Args:
            faces (bmesh.types.BMFace): selected faces to validate

        Returns:
            bool: whether the faces are valid
        """
        if faces:
            if not any([f.normal.z for f in faces]):
                return True
        return False

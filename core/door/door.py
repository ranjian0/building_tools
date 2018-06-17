import bmesh

from .door_types import make_door
from ...utils import (
    get_edit_mesh,
    kwargs_from_props,
    )


class Door:

    @classmethod
    def build(cls, props):
        """Use door types and properties to generate geometry

        Args:
            props (bpy.types.PropertyGroup): DoorProperty
        """
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [face for face in bm.faces if face.select]

        if cls.validate(faces):
            make_door(bm, faces, **kwargs_from_props(props))
            bmesh.update_edit_mesh(me, True)
            return {'FINISHED'}
        return {'CANCELLED'}

    @classmethod
    def validate(cls, faces):
        """ Ensure user has appropriate selection if any """
        if faces:
            if not any([f.normal.z for f in faces]):
                return True
        return False


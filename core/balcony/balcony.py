import bmesh

from .balcony_types import make_balcony
from ...utils import (
    get_edit_mesh,
    kwargs_from_props
    )

class Balcony:

    @classmethod
    def build(cls, context, props):
        """Use balcony types and properties to generate geomerty

        Args:
            context (bpy.context): blender context
            props   (bpy.types.PropertyGroup): BalconyProperty
        """

        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [face for face in bm.faces if face.select]

        if cls.validate(faces):
            make_balcony(bm, faces, **kwargs_from_props(props))
            bmesh.update_edit_mesh(me, True)
            return {'FINISHED'}
        return {'CANCELLED'}

    @classmethod
    def validate(cls, faces):
        """ Ensure user has appropriate selection if any """
        if faces:
            # -- ensure none are upward facing
            if not any([f.normal.z for f in faces]):
                return True
        return False


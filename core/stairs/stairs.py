import bmesh

from .stairs_types import make_stairs
from ...utils import (
    get_edit_mesh,
    kwargs_from_props
    )


class Stairs:

    @classmethod
    def build(cls, context, props):
        """Use stair types and properties to generate geometry

        Args:
            context (bpy.context): blender context
            props   (bpy.types.PropertyGroup): StairsProperty
        """
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [f for f in bm.faces if f.select]

        if cls.validate(faces):
            make_stairs(bm, faces, **kwargs_from_props(props))
            bmesh.update_edit_mesh(me, True)
            return {'FINISHED'}
        return {'CANCELLED'}

    @classmethod
    def validate(cls, faces):
        if faces:
            if not any([f.normal.z for f in faces]):
                return True
        return False

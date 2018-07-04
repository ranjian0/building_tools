import bpy
import bmesh

from ...utils import (
    get_edit_mesh,
    kwargs_from_props
    )

class Roof:

    @classmethod
    def build(cls, context, props):
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)

        if cls.validate(bm):

            bmesh.update_edit_mesh(me, True)
            return {'FINISHED'}
        return {'CANCELLED'}

    @classmethod
    def validate(cls, bm):
        """ Ensure valid user selection if any """
        faces = [f for f in bm.faces if f.select]
        if faces:
            if all([f.normal.z for f in faces]):
                return True
        return False

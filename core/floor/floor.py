import bpy
import bmesh
from .floor_types import make_floors

from ...utils import (
    select,
    get_edit_mesh,
    kwargs_from_props,
    material_set_faces,
    create_material_group
    )


class Floor:
    has_mat_groups = False

    @classmethod
    def build(cls, context, props):
        """Use floor types and properties to create geometry

        Args:
            context (bpy.context): blender context
            props   (bpy.types.PropertyGroup): FloorProperty
        """

        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)

        if cls.validate(bm):
            if any([f for f in bm.faces if f.select]):
                faces = make_floors(bm, None, **kwargs_from_props(props))
            else:
                edges = [e for e in bm.edges if e.is_boundary]
                faces = make_floors(bm, edges, **kwargs_from_props(props))
            bmesh.update_edit_mesh(me, True)
            cls.create_materials(context, *faces)
            return {'FINISHED'}
        return {'CANCELLED'}

    @classmethod
    def validate(cls, bm):
        """ Validate input if any """
        if len(list({v.co.z for v in bm.verts})) == 1:
            return True
        elif any([f for f in bm.faces if f.select]):
            return True
        return False

    @classmethod
    def create_materials(cls, context, slab_faces, wall_faces):
        if not cls.has_mat_groups:
            smat = create_material_group(context.object, "slab")
            material_set_faces(context.object, smat, slab_faces)
            wmat = create_material_group(context.object, "wall")
            material_set_faces(context.object, wmat, wall_faces)
            cls.has_mat_groups = True

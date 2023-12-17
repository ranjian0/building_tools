import bpy
import bmesh

from ..materialgroup import (
    MaterialGroup,
    add_material_group,
    verify_matgroup_attribute_for_object,
)

from .stairs_types import create_stairs
from .stairs_props import StairsProperty
from ...utils import crash_safe, get_edit_mesh
from ...utils import get_selected_face_dimensions


class BTOOLS_OT_add_stairs(bpy.types.Operator):
    """Create stairs from selected faces"""

    bl_idname = "btools.add_stairs"
    bl_label = "Add Stairs"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=StairsProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        self.props.init(get_selected_face_dimensions(context))
        return build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)


@crash_safe
def build(context, prop):
    verify_matgroup_attribute_for_object(context.object)
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    faces = [f for f in bm.faces if f.select]

    if validate_stair_faces(faces):
        add_stairs_matgroup()
        if create_stairs(bm, faces, prop):
            bmesh.update_edit_mesh(me, loop_triangles=True)
            return {"FINISHED"}

    bmesh.update_edit_mesh(me, loop_triangles=True)
    return {"CANCELLED"}


def add_stairs_matgroup():
    add_material_group(MaterialGroup.STAIRS)


def validate_stair_faces(faces):
    if faces:
        if not any([round(f.normal.z, 1) for f in faces]):
            return True
    return False

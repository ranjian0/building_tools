import bpy
import bmesh

from ..layers import ensure_layers_for_object
from ..materialgroup import MaterialGroup, add_material_group

from ...utils import (
    crash_safe,
    is_rectangle,
    get_edit_mesh,
)

from .multigroup_types import create_multigroup
from .multigroup_props import MultigroupProperty
from ...utils import get_selected_face_dimensions


class BTOOLS_OT_add_multigroup(bpy.types.Operator):
    """Create multiple door/window group from selected faces"""

    bl_idname = "btools.add_multigroup"
    bl_label = "Add Multigroup"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=MultigroupProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        self.props.init(get_selected_face_dimensions(context))
        return build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)


@crash_safe
def build(context, props):
    ensure_layers_for_object(context.object)
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    faces = validate_multigroup_faces([face for face in bm.faces if face.select])
    if faces:
        add_multigroup_matgroups()
        if create_multigroup(bm, faces, props):
            bmesh.update_edit_mesh(me, loop_triangles=True)
            return {"FINISHED"}

    bmesh.update_edit_mesh(me, loop_triangles=True)
    return {"CANCELLED"}


def add_multigroup_matgroups():
    groups = MaterialGroup.DOOR, MaterialGroup.WINDOW, MaterialGroup.FRAME
    add_material_group(groups)


def validate_multigroup_faces(faces):
    """Filter out invalid faces"""
    # -- remove upward facing faces
    faces = list(filter(lambda f: abs(round(f.normal.z, 3)) == 0.0, faces))
    # -- remove non-rectangular faces
    faces = list(filter(lambda f: is_rectangle(f), faces))
    return faces

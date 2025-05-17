import bpy
import bmesh

from ...utils import (
    crash_safe,
    is_rectangle,
    get_edit_mesh,
)

from .fill_types import add_fill
from .fill_props import FillProperty
from ..layers import ensure_layers_for_object


class BTOOLS_OT_add_fill(bpy.types.Operator):
    """Add fill to selected faces"""

    bl_idname = "btools.add_fill"
    bl_label = "Add Fill"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=FillProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        return build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)


@crash_safe
def build(context, props):
    ensure_layers_for_object(context.object)
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    faces = validate_fill_faces([face for face in bm.faces if face.select])
    if faces:
        if add_fill(bm, faces, props):
            bmesh.update_edit_mesh(me, loop_triangles=True)
            return {"FINISHED"}

    bmesh.update_edit_mesh(me, loop_triangles=True)
    return {"CANCELLED"}


def validate_fill_faces(faces):
    """Filter out invalid faces"""
    # -- remove upward facing faces
    faces = list(filter(lambda f: abs(round(f.normal.z, 3)) == 0.0, faces))
    # -- remove non-rectangular faces
    faces = list(filter(lambda f: is_rectangle(f), faces))
    return faces

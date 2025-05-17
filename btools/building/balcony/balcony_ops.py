import bpy
import bmesh

from ..layers import ensure_layers_for_object
from ..materialgroup import (
    MaterialGroup,
    add_material_group,
)

from .balcony_types import create_balcony
from .balcony_props import BalconyProperty
from ...utils import get_edit_mesh, crash_safe
from ...utils import get_selected_face_dimensions


class BTOOLS_OT_add_balcony(bpy.types.Operator):
    """Create a balcony from selected faces"""

    bl_idname = "btools.add_balcony"
    bl_label = "Add Balcony"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=BalconyProperty)

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
    ensure_layers_for_object(context.object)
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    faces = [face for face in bm.faces if face.select]

    if validate_balcony_faces(faces):
        add_balcony_matgroups()
        create_balcony(bm, faces, prop)
        bmesh.update_edit_mesh(me, loop_triangles=True)
        return {"FINISHED"}

    bmesh.update_edit_mesh(me, loop_triangles=True)
    return {"CANCELLED"}


def add_balcony_matgroups():
    groups = MaterialGroup.BALCONY
    add_material_group(groups)


def validate_balcony_faces(faces):
    if faces:
        # -- ensure none are upward facing
        if not any([round(f.normal.z, 1) for f in faces]):
            return True
    return False

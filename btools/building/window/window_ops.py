import bpy
import bmesh

from ..facemap import (
    FaceMap,
    add_facemap_for_groups,
    verify_facemaps_for_object,
)

from .window_types import create_window
from .window_props import WindowProperty
from ...utils import get_selected_face_dimensions
from ...utils import crash_safe, get_edit_mesh, is_rectangle


class BTOOLS_OT_add_window(bpy.types.Operator):
    """Create window from selected faces"""

    bl_idname = "btools.add_window"
    bl_label = "Add Window"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=WindowProperty)

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
    verify_facemaps_for_object(context.object)
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    faces = validate_window_faces([face for face in bm.faces if face.select])
    if faces:
        add_window_facemaps()
        if create_window(bm, faces, prop):
            bmesh.update_edit_mesh(me, loop_triangles=True)
            return {"FINISHED"}

    bmesh.update_edit_mesh(me, loop_triangles=True)
    return {"CANCELLED"}


def add_window_facemaps():
    groups = FaceMap.WINDOW, FaceMap.FRAME
    add_facemap_for_groups(groups)


def validate_window_faces(faces):
    """ Filter out invalid faces """
    # -- remove non-rectangular faces
    faces = list(filter(lambda f: is_rectangle(f), faces))
    # -- remove faces that are perpendicular to Z+
    faces = list(filter(lambda f: round(abs(f.normal.z), 2) != 1.0, faces))
    return faces

import bmesh
import bpy

from ...utils import crash_safe, get_edit_mesh
from ..materialgroup import verify_matgroup_attribute_for_object
from .interior_props import InteriorProperty
from .interior_types import create_partitions


class BTOOLS_OT_add_partitions(bpy.types.Operator):
    """Add interior partitions to the selected floor face"""

    bl_idname = "btools.add_partitions"
    bl_label = "Add Partitions"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=InteriorProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        return build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)


@crash_safe
def build(context, props):
    verify_matgroup_attribute_for_object(context.object)
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    faces = [f for f in bm.faces if f.select]

    # XXX partitions need upward-facing base faces
    for f in faces:
        if f.normal.z < 0:
            f.normal_flip()

    if validate_partition_faces(bm):
        create_partitions(bm, faces, props)
        bmesh.update_edit_mesh(me, loop_triangles=True)
        return {"FINISHED"}

    bmesh.update_edit_mesh(me, loop_triangles=True)
    return {"CANCELLED"}


def validate_partition_faces(bm):
    faces = [f for f in bm.faces if f.select]
    if faces:
        return all(round(f.normal.z, 1) for f in faces)
    return False

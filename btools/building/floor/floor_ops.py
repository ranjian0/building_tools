import bpy
import bmesh

from ..facemap import (
    FaceMap,
    clear_empty_facemaps,
    add_facemap_for_groups,
    verify_facemaps_for_object,
)

from ...utils import (
    select,
    crash_safe,
    get_edit_mesh,
)

from .floor_types import create_floors
from .floor_props import FloorProperty


class BTOOLS_OT_add_floors(bpy.types.Operator):
    """Create floors from the current edit mesh"""

    bl_idname = "btools.add_floors"
    bl_label = "Add Floors"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=FloorProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        return build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)


@crash_safe
def build(context, prop):
    verify_facemaps_for_object(context.object)

    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    # XXX Fix normals if they are inverted(Z-)
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()

    if validate_floor_faces(bm):
        add_floor_facemaps(context, prop)
        selected_faces = [f for f in bm.faces if f.select]
        if selected_faces:
            create_floors(bm, selected_faces, prop)
            select(bm.faces, False)
        else:
            all_faces = [f for f in bm.faces]
            create_floors(bm, all_faces, prop)
        bmesh.update_edit_mesh(me, loop_triangles=True)
        return {"FINISHED"}

    bmesh.update_edit_mesh(me, loop_triangles=True)
    return {"CANCELLED"}


def add_floor_facemaps(context, prop):
    clear_empty_facemaps(context)
    groups = FaceMap.WALLS, FaceMap.ROOF
    if prop.add_slab:
        groups += (FaceMap.SLABS,)
    if prop.add_columns:
        groups += (FaceMap.COLUMNS,)
    add_facemap_for_groups(groups)


def validate_floor_faces(bm):
    if any([f for f in bm.faces if f.select]):
        selection = [f for f in bm.faces if f.select]
        if len({round(v.co.z, 4) for f in selection for v in f.verts}) == 1:
            return True
    elif len({round(v.co.z, 4) for v in bm.verts}) == 1:
        return True
    return False

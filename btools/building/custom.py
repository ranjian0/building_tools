"""
Tools to allow users to place custom meshes on a building
"""
import bpy
import math
import bmesh
from mathutils import Matrix, Vector
from bpy.props import PointerProperty

from ..utils import (
    select,
    local_xyz,
    calc_verts_median,
    calc_face_dimensions,
    bmesh_from_active_object,
    subdivide_face_vertically,
    subdivide_face_horizontally,
    get_selected_face_dimensions,
)

from .generic import CountProperty, SizeOffsetProperty


class CustomObjectProperty(bpy.types.PropertyGroup):
    count: CountProperty
    size_offset: PointerProperty(type=SizeOffsetProperty)

    def init(self, wall_dimensions):
        self["wall_dimensions"] = wall_dimensions
        self.size_offset.init(
            (self["wall_dimensions"][0] / self.count, self["wall_dimensions"][1]),
            default_size=(1.0, 1.0),
            default_offset=(0.0, 0.0),
        )

    def draw(self, context, layout):
        box = layout.box()
        self.size_offset.draw(context, box)

        layout.prop(self, "count")


class BTOOLS_OT_add_custom(bpy.types.Operator):
    """Place custom meshes on the selected faces"""

    bl_idname = "btools.add_custom"
    bl_label = "Add Custom"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: PointerProperty(type=CustomObjectProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        custom_obj = context.scene.btools_custom_object
        if not custom_obj:
            # XXX Custom object has not been assigned
            print(custom_obj)
            self.report({'INFO'}, "No Object Selected!")
            return {"CANCELLED"}

        self.props.init(get_selected_face_dimensions(context))
        place_custom_object(context, self.props, custom_obj)
        return {'FINISHED'}

    def draw(self, context):
        self.props.draw(context, self.layout)


def place_custom_object(context, prop, custom_obj):
    with bmesh_from_active_object(context) as bm:
        # -- get all selected faces
        faces = [face for face in bm.faces if face.select]

        for face in faces:
            face.select = False
            # XXX subdivide horizontally for array
            array_faces = subdivide_face_horizontally(bm, face, widths=[prop.size_offset.size.x]*prop.count)

            for aface in array_faces:
                # XXX Create split for size offset
                split_face = create_split(bm, aface, prop.size_offset.size, prop.size_offset.offset)
                # Place custom object mesh
                place_object_on_face(bm, split_face, custom_obj, prop)

    return {"FINISHED"}


def duplicate_into_bm(bm, obj):
    """ Copy all the mesh data in obj to the bm
    Return the newly inserted faces
    """
    initial_faces = set(bm.faces)
    bm.from_mesh(obj.data.copy())
    return list(set(bm.faces) - initial_faces)


# TODO(ranjian0) refactor function (duplicated from create_window_split)
def create_split(bm, face, size, offset):
    """Use properties from SplitOffset to subdivide face into regular quads
    """
    wall_w, wall_h = calc_face_dimensions(face)
    # horizontal split
    h_widths = [wall_w/2 + offset.x - size.x/2, size.x, wall_w/2 - offset.x - size.x/2]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical split
    v_width = [wall_h/2 + offset.y - size.y/2, size.y, wall_h/2 - offset.y - size.y/2]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_width)

    return v_faces[1]


def place_object_on_face(bm, face, custom_obj, prop):
    """ Place the custom_object mesh flush on the face
    """
    # XXX get mesh from custom_obj into bm
    custom_faces = duplicate_into_bm(bm, custom_obj)
    custom_verts = list({v for f in custom_faces for v in f.verts})
    select(custom_faces, False)

    # (preprocess)calculate bounds of the object
    sort_x = sorted([v.co.x for v in custom_verts])
    sort_y = sorted([v.co.y for v in custom_verts])
    current_width = sort_x[-1] - sort_x[0]
    current_height = sort_y[-1] - sort_y[1]

    # -- move the custom faces into proper position on this face
    normal = face.normal.copy()
    median = face.calc_center_median()
    bmesh.ops.rotate(
        bm, verts=custom_verts,
        cent=calc_verts_median(custom_verts),
        matrix=Matrix.Rotation(math.pi / 2, 4, normal.cross(Vector((0, 0, -1))))
    )

    # -- calculate margin to make custom objes flush with this face
    # TODO(ranjian0) investigate this (current theory is order of scale, rotate, translate)
    diff = max(normal.dot(v.co) for v in custom_verts)
    diff_norm = diff * normal           # distance between face median and object median along normal
    diff_up = diff * Vector((0, 0, 1))  # distance between face median and object median along z+
    bmesh.ops.translate(bm, verts=custom_verts, vec=median - diff_norm + diff_up)

    # -- scale to size
    x_dir, y_dir, z_dir = local_xyz(face)
    target_width, target_height = prop.size_offset.size

    # --scale
    scale_x = x_dir * (target_width / current_width)
    scale_y = y_dir * (target_height / current_height)
    scale_z = Vector(map(abs, z_dir))
    bmesh.ops.scale(
        bm, verts=custom_verts, vec=scale_x + scale_y + scale_z,
        space=Matrix.Translation(-calc_verts_median(custom_verts))
    )

    # -- clean up
    bmesh.ops.delete(bm, geom=[face], context="FACES_ONLY")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)


classes = (CustomObjectProperty, BTOOLS_OT_add_custom)


def register_custom():
    bpy.types.Scene.btools_custom_object = PointerProperty(
        type=bpy.types.Object, description="Object to use for custom placement")

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_custom():
    del bpy.types.Scene.btools_custom_object

    for cls in classes:
        bpy.utils.unregister_class(cls)

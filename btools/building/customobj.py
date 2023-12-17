"""
Tools to allow users to place custom meshes on a building
"""
import bpy
import bmesh
from mathutils import Matrix, Vector
from bpy.props import PointerProperty

from .facemap import FaceMap, add_faces_to_map, add_facemap_for_groups

from ..utils import (
    select,
    local_xyz,
    bm_to_obj,
    crash_safe,
    bm_from_obj,
    popup_message,
    calc_faces_median,
    calc_verts_median,
    get_bounding_verts,
    calc_face_dimensions,
    bmesh_from_active_object,
    subdivide_face_vertically,
    subdivide_face_horizontally,
    get_selected_face_dimensions,
)
from ..utils import VEC_UP
from .array import ArrayProperty, ArrayGetSet
from .sizeoffset import SizeOffsetProperty, SizeOffsetGetSet


class CustomObjectProperty(bpy.types.PropertyGroup, SizeOffsetGetSet, ArrayGetSet):
    array: PointerProperty(type=ArrayProperty)
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

        layout.prop(self.array, "count")


@crash_safe
def add_custom_execute(self, context):
    custom_obj = context.scene.btools_custom_object
    if not custom_obj:
        # Custom object has not been assigned
        self.report({"INFO"}, "No Object Selected!")
        return {"CANCELLED"}

    if custom_obj.users == 0 or custom_obj.name not in context.view_layer.objects:
        # Object was already deleted
        self.report({"INFO"}, "Object has been deleted!")
        return {"CANCELLED"}

    self.props.init(get_selected_face_dimensions(context))

    apply_transforms(context, custom_obj)
    place_custom_object(context, self.props, custom_obj)
    transfer_materials(custom_obj, context.object)
    return {"FINISHED"}


class BTOOLS_OT_add_custom(bpy.types.Operator):
    """Place custom meshes on the selected faces"""

    bl_idname = "btools.add_custom"
    bl_label = "Add Custom Geometry"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: PointerProperty(type=CustomObjectProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        add_facemap_for_groups([FaceMap.CUSTOM])
        return add_custom_execute(self, context)

    def draw(self, context):
        self.props.draw(context, self.layout)


def apply_transforms(context, obj):
    # -- store the current active object
    mode_previous = context.mode
    active_previous = context.active_object

    # -- switch to object mode, if we are not already there
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    # -- make obj the active object and select it
    bpy.context.view_layer.objects.active = obj
    select(bpy.context.view_layer.objects, False)
    obj.select_set(True)

    # -- apply transform
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # -- resume the previous state
    bpy.context.view_layer.objects.active = active_previous
    select(bpy.context.view_layer.objects, False)
    active_previous.select_set(True)
    bpy.ops.object.mode_set(mode=mode_previous.replace("_MESH", ""))


def place_custom_object(context, prop, custom_obj):
    with bmesh_from_active_object(context) as bm:
        faces = [face for face in bm.faces if face.select]

        for face in faces:
            face.select = False
            # No support for upward/downward facing
            if face.normal.z:
                popup_message(
                    "Faces with Z+/Z- normals not supported!",
                    title="Invalid Face Selection",
                )
                continue

            array_faces = subdivide_face_horizontally(
                bm, face, widths=[prop.size_offset.size.x] * prop.count
            )
            for aface in array_faces:
                # -- Create split and place obj
                split_face = create_split(
                    bm, aface, prop.size_offset.size, prop.size_offset.offset
                )
                place_object_on_face(bm, split_face, custom_obj, prop)

        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)


def transfer_materials(from_object, to_obj):
    """Transfer materials from 'from_object' to 'to_object'"""
    materials = from_object.data.materials
    if not materials:
        return

    # -- copy materials
    to_mats = to_obj.data.materials
    if not to_mats:
        # -- to_obj has no materials
        list(map(to_mats.append, materials))
    else:
        # -- to_obj has some materials, ensure we are not duplicating
        for mat in materials:
            if mat.name not in to_mats:
                to_mats.append(mat)

    def mat_name_from_idx(idx):
        for i, m in enumerate(materials):
            if i == idx:
                return m.name.encode()
        return "".encode()

    # -- store material names on the face layer
    bm = bm_from_obj(from_object)
    bm.faces.layers.string.verify()
    mat_name = bm.faces.layers.string.active
    for face in bm.faces:
        face[mat_name] = mat_name_from_idx(face.material_index)
    bm_to_obj(bm, from_object)


def duplicate_into_bm(bm, obj):
    """Copy all the mesh data in obj to the bm
    Return the newly inserted faces
    """
    max_index = len(bm.faces)
    bm.from_mesh(obj.data.copy())
    return [f for f in bm.faces if f.index >= max_index]


# TODO(ranjian0) refactor function (duplicated from create_window_split)
def create_split(bm, face, size, offset):
    """Use properties from SplitOffset to subdivide face into regular quads"""
    wall_w, wall_h = calc_face_dimensions(face)
    # horizontal split
    h_widths = [
        wall_w / 2 + offset.x - size.x / 2,
        size.x,
        wall_w / 2 - offset.x - size.x / 2,
    ]
    h_faces = subdivide_face_horizontally(bm, face, h_widths)
    # vertical split
    v_width = [
        wall_h / 2 + offset.y - size.y / 2,
        size.y,
        wall_h / 2 - offset.y - size.y / 2,
    ]
    v_faces = subdivide_face_vertically(bm, h_faces[1], v_width)

    return v_faces[1]


def place_object_on_face(bm, face, custom_obj, prop):
    """Place the custom_object mesh flush on the face"""
    # XXX get mesh from custom_obj into bm
    face_idx = face.index
    custom_faces = duplicate_into_bm(bm, custom_obj)
    face = [f for f in bm.faces if f.index == face_idx].pop()  # restore reference
    add_faces_to_map(bm, custom_faces, FaceMap.CUSTOM)
    custom_verts = list({v for f in custom_faces for v in f.verts})

    # (preprocess)calculate bounds of the object
    # NOTE: bounds are calculated before any transform is made
    dims = custom_obj.dimensions
    current_size = [max(dims.x, dims.y), dims.z]

    # -- move the custom faces into proper position on this face
    transform_parallel_to_face(bm, custom_faces, face)
    scale_to_size(
        bm, custom_verts, current_size, prop.size_offset.size, local_xyz(face)
    )

    # cleanup
    bmesh.ops.delete(bm, geom=[face], context="FACES_ONLY")


def get_coplanar_faces(face_verts):
    """Determine extent faces that should be coplanar to walls"""
    bounds = get_bounding_verts(face_verts)
    coplanar_faces = (
        list(bounds.topleft.link_faces)
        + list(bounds.topright.link_faces)
        + list(bounds.botleft.link_faces)
        + list(bounds.botright.link_faces)
    )
    return set(coplanar_faces)


def calc_coplanar_median(face_verts):
    """Determine the median point for coplanar faces"""
    return calc_faces_median(get_coplanar_faces(face_verts))


def calc_coplanar_normal(faces):
    face_verts = list({v for f in faces for v in f.verts})
    coplanar_faces = get_coplanar_faces(face_verts)
    normals = {f.normal.copy().to_tuple(3) for f in coplanar_faces}
    return Vector(normals.pop())


def transform_parallel_to_face(bm, custom_faces, target_face):
    """Move and rotate verts(mesh) so that it lies with it's
    forward-extreme faces parallel to `face`
    """
    target_normal = target_face.normal.copy()
    target_median = target_face.calc_center_median()

    verts = list({v for f in custom_faces for v in f.verts})
    verts_median = calc_verts_median(verts)
    custom_normal = calc_coplanar_normal(custom_faces)
    try:
        angle = target_normal.xy.angle_signed(custom_normal.xy)
    except ValueError:
        # TODO(ranjian0) Support all mesh shapes when placing along face
        angle = 0

    bmesh.ops.rotate(
        bm, verts=verts, cent=verts_median, matrix=Matrix.Rotation(angle, 4, VEC_UP)
    )

    # -- determine the median of the faces that should be coplanar to the walls
    coplanar_median = calc_coplanar_median(verts)
    coplanar_median.z = (
        verts_median.z
    )  # Compensate on Z axis for any coplanar faces not considered in calculations

    # -- move the custom faces to the target face based on coplanar median
    transform_diff = target_median - coplanar_median
    bmesh.ops.translate(bm, verts=verts, vec=transform_diff)


def scale_to_size(bm, verts, current_size, target_size, local_dir):
    """Scale verts to target size along local direction (x and y)"""
    x_dir, y_dir, z_dir = local_dir
    target_width, target_height = target_size
    current_width, current_height = current_size

    # --scale
    scale_x = x_dir * (target_width / current_width)
    scale_y = y_dir * (target_height / current_height)
    scale_z = Vector(map(abs, z_dir))
    bmesh.ops.scale(
        bm,
        verts=verts,
        vec=scale_x + scale_y + scale_z,
        space=Matrix.Translation(-calc_verts_median(verts)),
    )


def set_face_materials(bm, faces):
    mat_name = bm.faces.layers.string.active
    if not mat_name:
        return

    obj_mats = bpy.context.object.data.materials
    for f in faces:
        mat = obj_mats.get(f[mat_name].decode())
        f.material_index = list(obj_mats).index(mat)


classes = (CustomObjectProperty, BTOOLS_OT_add_custom)


def register_custom():
    bpy.types.Scene.btools_custom_object = PointerProperty(
        type=bpy.types.Object, description="Object to use for custom placement"
    )

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_custom():
    del bpy.types.Scene.btools_custom_object

    for cls in classes:
        bpy.utils.unregister_class(cls)

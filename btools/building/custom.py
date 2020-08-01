"""
Tools to allow users to place custom meshes on a building
"""
import bpy
import bmesh
from mathutils import Matrix, Vector
from bpy.props import PointerProperty

from ..utils import (
    select,
    local_xyz,
    bm_to_obj,
    bm_from_obj,
    calc_verts_median,
    calc_face_dimensions,
    create_object_material,
    bmesh_from_active_object,
    subdivide_face_vertically,
    subdivide_face_horizontally,
    get_selected_face_dimensions,
)
from ..utils import VEC_UP, VEC_FORWARD
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
    """Place custom meshes on the selected faces
    Mesh must be forward facing(Y+ axis)"""

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
            self.report({'INFO'}, "No Object Selected!")
            return {"CANCELLED"}

        self.props.init(get_selected_face_dimensions(context))

        transfer_materials(custom_obj, context.object)
        place_custom_object(context, self.props, custom_obj)
        return {'FINISHED'}

    def draw(self, context):
        self.props.draw(context, self.layout)


def place_custom_object(context, prop, custom_obj):
    with bmesh_from_active_object(context) as bm:
        # -- get all selected faces
        faces = [face for face in bm.faces if face.select]
        face_data = [f.verts for f in faces]

        for idx, face in enumerate(faces):
            # XXX TODO(ranjian0) investigate why reference was lost here
            if not face.is_valid:
                face = bm.faces.get(face_data[idx])

            face.select = False
            # XXX subdivide horizontally for array
            array_faces = subdivide_face_horizontally(bm, face, widths=[prop.size_offset.size.x]*prop.count)

            for aface in array_faces:
                # XXX Create split for size offset
                split_face = create_split(bm, aface, prop.size_offset.size, prop.size_offset.offset)
                # Place custom object mesh
                place_object_on_face(bm, split_face, custom_obj, prop)

        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    return {"FINISHED"}


def transfer_materials(from_object, to_obj):
    """ Transfer materials from 'from_object' to 'to_object'
    """
    materials = from_object.data.materials
    if not materials:
        return

    # -- copy materials
    to_mats = to_obj.data.materials
    if not to_mats:
        # -- to_obj has no materials
        create_object_material(to_obj, "default_mat")
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
    """ Copy all the mesh data in obj to the bm
    Return the newly inserted faces
    """
    initial_faces = {f.index for f in bm.faces}
    bm.from_mesh(obj.data.copy())
    return [f for f in bm.faces if f.index not in initial_faces]


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
    verts = face.verts

    custom_faces = duplicate_into_bm(bm, custom_obj)
    select(custom_faces, False)
    set_face_materials(bm, custom_faces)

    # XXX TODO(ranjian0) reference to face changes here, why?
    if not face.is_valid:
        face = bm.faces.get(verts)

    custom_verts = list({v for f in custom_faces for v in f.verts})

    # (preprocess)calculate bounds of the object
    # NOTE: bounds are calculated before any transform is made
    *current_size, _ = calc_verts_bounds(custom_verts)

    # -- move the custom faces into proper position on this face
    transform_parallel_to_face(bm, custom_verts, face)

    # -- scale to size
    scale_to_size(
        bm, custom_verts,
        current_size, prop.size_offset.size, local_xyz(face)
    )

    # cleanup
    bmesh.ops.delete(bm, geom=[face], context="FACES_ONLY")


def calc_verts_bounds(verts):
    """ Determine the bounds size of the verts
    (assumes verts(mesh) is facing forward(y+))
    """
    sort_x = sorted([v.co.x for v in verts])
    sort_y = sorted([v.co.y for v in verts])
    sort_z = sorted([v.co.z for v in verts])
    width = sort_x[-1] - sort_x[0]
    height = sort_z[-1] - sort_z[1]
    depth = sort_y[-1] - sort_y[1]
    return width, height, depth


def transform_parallel_to_face(bm, verts, face):
    """ Move and rotate verts(mesh) so that it lies with it's
    forward-extreme faces parallel to `face`
    """
    normal = face.normal.copy()
    median = face.calc_center_median()
    angle = normal.xy.angle_signed(VEC_FORWARD.xy)
    bmesh.ops.rotate(
        bm, verts=verts,
        cent=calc_verts_median(verts),
        matrix=Matrix.Rotation(angle, 4, VEC_UP)
    )

    # -- calculate margin to make custom objes flush with this face
    # TODO(ranjian0) investigate this (current theory is order of scale, rotate, translate)
    diff = max(normal.dot(v.co) for v in verts)
    diff_norm = diff * normal           # distance between face median and object median along normal
    bmesh.ops.translate(bm, verts=verts, vec=median - diff_norm)


def scale_to_size(bm, verts, current_size, target_size, local_dir):
    """ Scale verts to target size along local direction (x and y)
    """
    x_dir, y_dir, z_dir = local_dir
    target_width, target_height = target_size
    current_width, current_height = current_size

    # --scale
    scale_x = x_dir * (target_width / current_width)
    scale_y = y_dir * (target_height / current_height)
    scale_z = Vector(map(abs, z_dir))
    bmesh.ops.scale(
        bm, verts=verts, vec=scale_x + scale_y + scale_z,
        space=Matrix.Translation(-calc_verts_median(verts))
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
        type=bpy.types.Object, description="Object to use for custom placement")

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_custom():
    del bpy.types.Scene.btools_custom_object

    for cls in classes:
        bpy.utils.unregister_class(cls)
